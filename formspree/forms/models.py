import hmac
import random
import hashlib
import datetime

from formspree.app import DB, redis_store
from formspree import settings
from formspree.utils import send_email, unix_time_for_12_months_from_now, \
                            next_url, IS_VALID_EMAIL, request_wants_json
from flask import url_for, render_template, g
from sqlalchemy.sql.expression import delete
from sqlalchemy import func
from werkzeug.datastructures import ImmutableMultiDict, \
                                    ImmutableOrderedMultiDict
from helpers import HASH, HASHIDS_CODEC, REDIS_COUNTER_KEY, \
                    http_form_to_dict, referrer_to_path, \
                    store_first_submission, fetch_first_submission, \
                    KEYS_NOT_STORED


class Form(DB.Model):
    __tablename__ = 'forms'

    id = DB.Column(DB.Integer, primary_key=True)
    hash = DB.Column(DB.String(32), unique=True)
    email = DB.Column(DB.String(120))
    host = DB.Column(DB.String(300))
    sitewide = DB.Column(DB.Boolean)
    disabled = DB.Column(DB.Boolean)
    confirm_sent = DB.Column(DB.Boolean)
    confirmed = DB.Column(DB.Boolean)
    counter = DB.Column(DB.Integer)
    owner_id = DB.Column(DB.Integer, DB.ForeignKey('users.id'))
    captcha_disabled = DB.Column(DB.Boolean)
    uses_ajax = DB.Column(DB.Boolean)

    owner = DB.relationship('User') # direct owner, defined by 'owner_id'
                                    # this property is basically useless. use .controllers
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
    STATUS_OVERLIMIT               = 3
    STATUS_REPLYTO_ERROR           = 4

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
        self.disabled = False
        self.uses_ajax = request_wants_json()
        self.captcha_disabled = False

    def __repr__(self):
        return '<Form %s, email=%s, host=%s>' % (self.id, self.email, self.host)

    @property
    def controllers(self):
        from formspree.users.models import User, Email
        by_email = DB.session.query(User) \
            .join(Email, User.id == Email.owner_id) \
            .join(Form, Form.email == Email.address) \
            .filter(Form.id == self.id)
        by_creation = DB.session.query(User) \
            .join(Form, User.id == Form.owner_id) \
            .filter(Form.id == self.id)
        return by_email.union(by_creation)

    @property
    def upgraded(self):
        upgraded_controllers = [i for i in self.controllers if i.upgraded]
        return len(upgraded_controllers) > 0

    @classmethod
    def get_with_hashid(cls, hashid):
        try:
            id = HASHIDS_CODEC.decode(hashid)[0]
            return cls.query.get(id)
        except IndexError:
            return None

    def send(self, data, keys, referrer):
        '''
        Sends form to user's email.
        Assumes sender's email has been verified.
        '''

        subject = data.get('_subject') or \
            'New submission from %s' % referrer_to_path(referrer)
        reply_to = (data.get(
            '_replyto',
            data.get('email', data.get('Email'))
        ) or '').strip()
        cc = data.get('_cc', None)
        next = next_url(referrer, data.get('_next'))
        spam = data.get('_gotcha', None)
        format = data.get('_format', None)

        # turn cc emails into array
        if cc:
            cc = [email.strip() for email in cc.split(',')]

        # prevent submitting empty form
        if not any(data.values()):
            return {'code': Form.STATUS_EMAIL_EMPTY}

        # return a fake success for spam
        if spam:
            g.log.info('Submission rejected.', gotcha=spam)
            return {'code': Form.STATUS_EMAIL_SENT, 'next': next}

        # validate reply_to, if it is not a valid email address, reject
        if reply_to and not IS_VALID_EMAIL(reply_to):
            g.log.info('Submission rejected. Reply-To is invalid.',
                       reply_to=reply_to)
            return {
                'code': Form.STATUS_REPLYTO_ERROR,
                'address': reply_to,
                'referrer': referrer
            }

        # increase the monthly counter
        request_date = datetime.datetime.now()
        self.increase_monthly_counter(basedate=request_date)

        # increment the forms counter
        self.counter = Form.counter + 1
        DB.session.add(self)

        # archive the form contents
        sub = Submission(self.id)
        sub.data = {key: data[key] for key in data if key not in KEYS_NOT_STORED}
        DB.session.add(sub)

        # commit changes
        DB.session.commit()

        # sometimes we'll delete all archived submissions over the limit
        if random.random() < settings.EXPENSIVELY_WIPE_SUBMISSIONS_FREQUENCY:
            records_to_keep = settings.ARCHIVED_SUBMISSIONS_LIMIT
            total_records = DB.session.query(func.count(Submission.id)) \
                .filter_by(form_id=self.id) \
                .scalar()

            if total_records > records_to_keep:
                newest = self.submissions.with_entities(Submission.id).limit(records_to_keep)
                DB.engine.execute(
                  delete('submissions'). \
                  where(Submission.form_id == self.id). \
                  where(~Submission.id.in_(newest))
                )

        # check if the forms are over the counter and the user is not upgraded
        overlimit = False
        monthly_counter = self.get_monthly_counter()
        if monthly_counter > settings.MONTHLY_SUBMISSIONS_LIMIT and not self.upgraded:
            overlimit = True

        if monthly_counter == int(settings.MONTHLY_SUBMISSIONS_LIMIT * 0.9) and not self.upgraded:
            # send email notification
            send_email(
                to=self.email,
                subject="[WARNING] Approaching submission limit",
                text=render_template('email/90-percent-warning.txt'),
                html=render_template('email/90-percent-warning.html'),
                sender=settings.DEFAULT_SENDER
            )

        now = datetime.datetime.utcnow().strftime('%I:%M %p UTC - %d %B %Y')
        if not overlimit:
            text = render_template('email/form.txt', data=data, host=self.host, keys=keys, now=now)
            # check if the user wants a new or old version of the email
            if format == 'plain':
                html = render_template('email/plain_form.html', data=data, host=self.host, keys=keys, now=now)
            else:
                html = render_template('email/form.html', data=data, host=self.host, keys=keys, now=now)
        else:
            if monthly_counter - settings.MONTHLY_SUBMISSIONS_LIMIT > 25:
                g.log.info('Submission rejected. Form over quota.', monthly_counter=monthly_counter)
                # only send this overlimit notification for the first 25 overlimit emails
                # after that, return an error so the user can know the website owner is not
                # going to read his message.
                return { 'code': Form.STATUS_OVERLIMIT }

            text = render_template('email/overlimit-notification.txt', host=self.host)
            html = render_template('email/overlimit-notification.html', host=self.host)

        result = send_email(
            to=self.email,
            subject=subject,
            text=text,
            html=html,
            sender=settings.DEFAULT_SENDER,
            reply_to=reply_to,
            cc=cc,
            headers={
                'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                'List-Unsubscribe': '<' + url_for(
                    'unconfirm_form',
                    form_id=self.id,
                    digest=self.unconfirm_digest(),
                    _external=True
                ) + '>'
            }
        )

        if not result[0]:
            g.log.warning('Failed to send email.',
                          reason=result[1], code=result[2])
            if result[1].startswith('Invalid replyto email address'):
                return {
                    'code': Form.STATUS_REPLYTO_ERROR,
                    'address': reply_to,
                    'referrer': referrer
                }

            return {
                'code': Form.STATUS_EMAIL_FAILED,
                'mailer-code': result[2],
                'error-message': result[1]
            }

        return {'code': Form.STATUS_EMAIL_SENT, 'next': next}

    def get_monthly_counter(self, basedate=None):
        basedate = basedate or datetime.datetime.now()
        month = basedate.month
        key = REDIS_COUNTER_KEY(form_id=self.id, month=month)
        counter = redis_store.get(key) or 0
        return int(counter)

    def increase_monthly_counter(self, basedate=None):
        basedate = basedate or datetime.datetime.now()
        month = basedate.month
        key = REDIS_COUNTER_KEY(form_id=self.id, month=month)
        redis_store.incr(key)
        redis_store.expireat(key, unix_time_for_12_months_from_now(basedate))

    def send_confirmation(self, store_data=None):
        '''
        Helper that actually creates confirmation nonce
        and sends the email to associated email. Renders
        different templates depending on the result
        '''

        g.log = g.log.new(form=self.id, to=self.email, host=self.host)
        g.log.debug('Confirmation.')
        if self.confirm_sent:
            g.log.debug('Previously sent.')
            return {'code': Form.STATUS_CONFIRMATION_DUPLICATED}

        # the nonce for email confirmation will be the hash when it exists
        # (whenever the form was created from a simple submission) or
        # a concatenation of HASH(email, id) + ':' + hashid
        # (whenever the form was created from the dashboard)
        id = str(self.id)
        nonce = self.hash or '%s:%s' % (HASH(self.email, id), self.hashid)
        link = url_for('confirm_email', nonce=nonce, _external=True)

        def render_content(ext):
            data, keys = None, None
            if store_data:
                if type(store_data) in (
                        ImmutableMultiDict, ImmutableOrderedMultiDict):
                    data, _ = http_form_to_dict(store_data)
                    store_first_submission(nonce, data)
                else:
                    store_first_submission(nonce, store_data)

            return render_template('email/confirm.%s' % ext,
                                   email=self.email,
                                   host=self.host,
                                   nonce_link=link,
                                   keys=keys)

        DB.session.add(self)
        DB.session.flush()

        result = send_email(
            to=self.email,
            subject='Confirm email for %s' % settings.SERVICE_NAME,
            text=render_content('txt'),
            html=render_content('html'),
            sender=settings.DEFAULT_SENDER,
            headers={
                'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                'List-Unsubscribe': '<' + url_for(
                    'unconfirm_form',
                    form_id=self.id,
                    digest=self.unconfirm_digest(),
                    _external=True
                ) + '>'
            }
        )
        g.log.debug('Confirmation email queued.')

        if not result[0]:
            return {'code': Form.STATUS_CONFIRMATION_FAILED}

        self.confirm_sent = True
        DB.session.add(self)
        DB.session.commit()

        return {'code': Form.STATUS_CONFIRMATION_SENT}

    @classmethod
    def confirm(cls, nonce):
        if ':' in nonce:
            # form created in the dashboard
            # nonce is another hash and the
            # hashid comes in the request.
            nonce, hashid = nonce.split(':')
            form = cls.get_with_hashid(hashid)
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

            stored_data = fetch_first_submission(nonce)
            if stored_data:
                form.send(stored_data, stored_data.keys(), form.host)

            return form

    @property
    def hashid(self):
        # A unique identifier for the form that maps to its id,
        # but doesn't seem like a sequential integer
        try:
            return self._hashid
        except AttributeError:
            if not self.id:
                raise Exception("this form doesn't have an id yet, commit it first.")
            self._hashid = HASHIDS_CODEC.encode(self.id)
        return self._hashid

    def unconfirm_digest(self):
        return hmac.new(
            settings.NONCE_SECRET,
            'id={}'.format(self.id),
            hashlib.sha256
        ).hexdigest()

    def unconfirm_with_digest(self, digest):
        if hmac.new(
            settings.NONCE_SECRET,
            'id={}'.format(self.id),
            hashlib.sha256
        ).hexdigest() != digest:
            return False

        self.confirmed = False
        DB.session.add(self)
        DB.session.commit()
        return True


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

    def __repr__(self):
        return '<Submission %s, form=%s, date=%s, keys=%s>' % \
            (self.id or 'with an id to be assigned', self.form_id, self.submitted_at.isoformat(), self.data.keys())
