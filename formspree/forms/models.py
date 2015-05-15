import urlparse
import datetime

from formspree.app import DB, redis_store
from formspree import settings, log
from formspree.utils import send_email, unix_time_for_12_months_from_now, next_url
from flask import url_for, render_template
from sqlalchemy.sql.expression import delete
from helpers import HASH, HASHIDS_CODEC, MONTHLY_COUNTER_KEY, http_form_to_dict, referrer_to_path

CODE_TEMPLATE = '''
<form action="{action}" method="POST">
    <input type="text" name="_gotcha" style="display:none" />
    <input type="email" name="email" placeholder="Your email">
    <textarea name="message" rows="5" placeholder="Your message"></textarea>
    <input type="submit" value="Send">
</form>
'''


class Form(DB.Model):
    __tablename__ = 'forms'

    id = DB.Column(DB.Integer, primary_key=True)
    hash = DB.Column(DB.String(32), unique=True)
    email = DB.Column(DB.String(120))
    host = DB.Column(DB.String(300))
    confirm_sent = DB.Column(DB.Boolean)
    confirmed = DB.Column(DB.Boolean)
    counter = DB.Column(DB.Integer)
    owner_id = DB.Column(DB.Integer, DB.ForeignKey('users.id'))

    owner = DB.relationship('User')
    submissions = DB.relationship('Submission',
        backref='form', lazy='dynamic', order_by=lambda: Submission.id.desc())

    '''
    When the form is created by a spontaneous submission, it is added to
    the table with a `host`, an `email` and a `hash` made of these two
    (+ a secret nonce).

    `hash` is UNIQUE because it is used to query these spontaneous forms
    when the form is going to be confirmed and whenever a new submission arrives.

    When a registered user POSTs to /forms, a new form is added to the table
    with an `email` (provided by the user) and an `owner_id`. Later, when this
    form receives its first submission and confirmation, `host` is added, so
    we can ensure that no one will submit to this same form from another host.

    `hash` is never added to these forms, because they could conflict with other
    forms, created by the spontaneous process, with the same email and host. So
    for these forms a different confirmation method is used (see below).
    '''

    STATUS_EMAIL_SENT              = 0
    STATUS_EMAIL_EMPTY             = 1
    STATUS_EMAIL_FAILED            = 2

    STATUS_CONFIRMATION_SENT       = 10
    STATUS_CONFIRMATION_DUPLICATED = 11
    STATUS_CONFIRMATION_FAILED     = 12

    def __init__(self, email, host=None, owner=None):
        if host:
            self.hash = HASH(email, host)
        elif owner:
            self.owner_id = owner.id
        else:
            raise Exception('cannot create form without a host and a owner. provide one of these.')
        self.email = email
        self.host = host
        self.confirm_sent = False
        self.confirmed = False
        self.counter = 0

    def __repr__(self):
        return '<Form %s, email=%s, host=%s>' % (self.id, self.email, self.host)

    def controlled_by(self, user):
        print 'user:', user.__dict__
        print 'user.forms:', [f.__dict__ for f in user.forms]
        print 'self:', self.__dict__
        return user.forms.filter(Form.id == self.id).count()

    def get_random_like_string(self):
        if not self.id:
            raise Exception("this form doesn't have an id yet, commit it first.")
        return HASHIDS_CODEC.encode(self.id)

    @classmethod
    def get_form_by_random_like_string(cls, random_like_string):
        id = HASHIDS_CODEC.decode(random_like_string)[0]
        return cls.query.get(id)

    def send(self, http_form, referrer):
        '''
        Sends form to user's email.
        Assumes sender's email has been verified.
        '''

        data, keys = http_form_to_dict(http_form)

        subject = data.get('_subject', 'New submission from %s' % referrer_to_path(referrer))
        reply_to = data.get('_replyto', data.get('email', data.get('Email', None)))
        cc = data.get('_cc', None)
        next = next_url(referrer, data.get('_next'))
        spam = data.get('_gotcha', None)

        # prevent submitting empty form
        if not any(data.values()):
            return { 'code': Form.STATUS_EMAIL_EMPTY }

        # return a fake success for spam
        if spam:
            return { 'code': Form.STATUS_EMAIL_SENT, 'next': next }

        # increase the monthly counter
        request_date = datetime.datetime.now()
        self.increase_monthly_counter(basedate=request_date)

        # increment the forms counter
        self.counter = Form.counter + 1
        DB.session.add(self)

        # archive the form contents
        sub = Submission(self.id)
        sub.data = data
        DB.session.add(sub)

        # commit changes
        DB.session.commit()

        # delete all archived submissions over the limit
        records_to_keep = settings.ARCHIVED_SUBMISSIONS_LIMIT
        newest = self.submissions.with_entities(Submission.id).limit(records_to_keep)
        DB.engine.execute(
          delete('submissions'). \
          where(Submission.form_id == self.id). \
          where(~Submission.id.in_(newest))
        )

        # check if the forms are over the counter and the user is not upgraded
        overlimit = False
        if self.get_monthly_counter(basedate=request_date) > settings.MONTHLY_SUBMISSIONS_LIMIT:
            if not self.owner or not self.owner.upgraded:
                overlimit = True

        now = datetime.datetime.utcnow().strftime('%I:%M %p UTC - %d %B %Y')
        if not overlimit:
            text = render_template('email/form.txt', data=data, host=self.host, keys=keys, now=now)
            html = render_template('email/form.html', data=data, host=self.host, keys=keys, now=now)
        else:
            text = render_template('email/overlimit-notification.txt', host=self.host)
            html = render_template('email/overlimit-notification.html', host=self.host)

        result = send_email(to=self.email,
                          subject=subject,
                          text=text,
                          html=html,
                          sender=settings.DEFAULT_SENDER,
                          reply_to=reply_to,
                          cc=cc)

        if not result[0]:
            return{ 'code': Form.STATUS_EMAIL_FAILED }

        return { 'code': Form.STATUS_EMAIL_SENT, 'next': next }

    def get_monthly_counter(self, basedate=None):
        basedate = basedate or datetime.datetime.now()
        month = basedate.month
        key = MONTHLY_COUNTER_KEY(form_id=self.id, month=month)
        counter = redis_store.get(key) or 0
        return int(counter)

    def increase_monthly_counter(self, basedate=None):
        basedate = basedate or datetime.datetime.now()
        month = basedate.month
        key = MONTHLY_COUNTER_KEY(form_id=self.id, month=month)
        redis_store.incr(key)
        redis_store.expireat(key, unix_time_for_12_months_from_now(basedate))

    def send_confirmation(self):
        '''
        Helper that actually creates confirmation nonce
        and sends the email to associated email. Renders
        different templates depending on the result
        '''

        log.debug('Sending confirmation')
        if self.confirm_sent:
            return { 'code': Form.STATUS_CONFIRMATION_DUPLICATED }

        # the nonce for email confirmation will be the hash when it exists
        # (whenever the form was created from a simple submission) or
        # a concatenation of HASH(email, id) + ':' + random_like_string
        # (whenever the form was created from the dashboard)
        id = str(self.id)
        nonce = self.hash or '%s:%s' % (HASH(self.email, id), self.get_random_like_string())
        link = url_for('confirm_email', nonce=nonce, _external=True)

        def render_content(type):
            return render_template('email/confirm.%s' % type,
                                      email=self.email,
                                      host=self.host,
                                      nonce_link=link)

        log.debug('Sending email')

        result = send_email(to=self.email,
                            subject='Confirm email for %s' % settings.SERVICE_NAME,
                            text=render_content('txt'),
                            html=render_content('html'),
                            sender=settings.DEFAULT_SENDER)

        log.debug('Sent')

        if not result[0]:
            return { 'code': Form.STATUS_CONFIRMATION_FAILED }

        self.confirm_sent = True
        DB.session.add(self)
        DB.session.commit()

        return { 'code': Form.STATUS_CONFIRMATION_SENT }

    @classmethod
    def confirm(cls, nonce):
        if ':' in nonce:
            # form created in the dashboard
            # nonce is another hash and the
            # random_like_string comes in the
            # request.
            nonce, rls = nonce.split(':')
            form = cls.get_form_by_random_like_string(rls)
            if HASH(form.email, str(form.id)) == nonce:
                pass
            else:
                form = None
        else:
            # normal form, nonce is HASH(email, host)
            form = cls.query.filter_by(hash=nonce).first()

        if form:
            form.confirmed = True
            DB.session.add(form)
            DB.session.commit()
            return form

    @property
    def action(self):
        return url_for('send', email_or_string=self.get_random_like_string(), _external=True)

    @property
    def code(self):
        return CODE_TEMPLATE.format(action=self.action)

    @property
    def is_new(self):
        return not self.host

    @property
    def status(self):
        if self.is_new:
            return 'new'
        elif self.confirmed:
            return 'confirmed'
        elif self.confirm_sent:
            return 'waiting_confirmation'

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.mutable import MutableDict

class Submission(DB.Model):
    __tablename__ = 'submissions'

    id = DB.Column(DB.Integer, primary_key=True)
    submitted_at = DB.Column(DB.DateTime)
    form_id = DB.Column(DB.Integer, DB.ForeignKey('forms.id'))
    data = DB.Column(MutableDict.as_mutable(JSON))

    def __init__(self, form_id):
        self.submitted_at = datetime.datetime.utcnow()
        self.form_id = form_id
