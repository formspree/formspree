'''
database and its structure

'''
from formspree.app import DB, REDIS
from formspree import settings, log
from formspree.utils import unix_time_for_12_months_from_now
from flask import url_for, render_template
from helpers import HASH, MONTHLY_COUNTER_KEY, http_form_to_dict, referrer_to_path, send_email
import datetime

from formspree.users.models import User

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

    STATUS_EMAIL_SENT              = 0
    STATUS_EMAIL_EMPTY             = 1
    STATUS_EMAIL_FAILED            = 2

    STATUS_CONFIRMATION_SENT       = 10
    STATUS_CONFIRMATION_DUPLICATED = 11
    STATUS_CONFIRMATION_FAILED     = 12

    def __init__(self, email, host):
        self.hash = HASH(email, host)
        self.email = email
        self.host = host
        self.confirm_sent = False
        self.confirmed = False
        self.counter = 0

    def __repr__(self):
        return '<Form %s, email=%s, host=%s>' % (self.id, self.email, self.host)

    def send(self, http_form, referrer):
        '''
        Sends form to user's email.
        Assumes sender's email has been verified.
        '''

        data, keys = http_form_to_dict(http_form)

        subject = data.get('_subject', 'New submission from %s' % referrer_to_path(referrer))
        reply_to = data.get('_replyto', data.get('email', data.get('Email', None)))
        cc = data.get('_cc', None)
        next = data.get('_next', url_for('thanks', next=referrer))
        spam = data.get('_gotcha', None)

        # prevent submitting empty form
        if not any(data.values()):
            return { 'code': Form.STATUS_EMAIL_EMPTY }

        # return a fake success for spam
        if spam:
            return { 'code': Form.STATUS_EMAIL_SENT, 'next': next }

        # increment the forms counter
        self.counter = Form.counter + 1
        DB.session.add(self)
        DB.session.commit()

        # increase the monthly counter
        self.increase_monthly_counter()

        # check if the forms are over the counter and the user is not upgraded
        overlimit = False
        if self.get_monthly_counter() > settings.MONTHLY_SUBMISSIONS_LIMIT:
            if not self.owner or not self.owner.upgraded:
                overlimit = True

        now = datetime.datetime.utcnow().strftime('%I:%M %p UTC - %d %B %Y')
        if not overlimit:
            text = render_template('email/form.txt', data=data, host=self.host, keys=keys, now=now)
            html = render_template('email/form.html', data=data, host=self.host, keys=keys, now=now)
        else:
            text = render_template('email/overlimit-notification.txt', data=data, host=self.host, keys=keys, now=now)
            html = render_template('email/overlimit-notification.html', data=data, host=self.host, keys=keys, now=now)

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

    def get_monthly_counter(self, month=None):
        month = month or datetime.date.today().month
        key = MONTHLY_COUNTER_KEY(form_id=self.id, month=month)
        counter = REDIS.get(key) or 0
        return int(counter)

    def increase_monthly_counter(self):
        month = datetime.date.today().month
        key = MONTHLY_COUNTER_KEY(form_id=self.id, month=month)
        REDIS.incr(key)
        REDIS.expireat(key, unix_time_for_12_months_from_now())

    @staticmethod
    def send_confirmation(email, host):
        '''
        Helper that actually creates confirmation nonce
        and sends the email to associated email. Renders
        different templates depending on the result
        '''
        form = Form.query.filter_by(hash=HASH(email, host)).first()

        log.debug('Sending confirmation')
        if form and form.confirm_sent:
            return { 'code': Form.STATUS_CONFIRMATION_DUPLICATED }

        link = url_for('confirm_email', nonce=HASH(email, host), _external=True)

        def render_content(type):
            return render_template('email/confirm.%s' % type,
                                      email=email,
                                      host=host,
                                      nonce_link=link)

        log.debug('Sending email')

        result = send_email(to=email,
                             subject='Confirm email for %s' % settings.SERVICE_NAME,
                             text=render_content('txt'),
                             html=render_content('html'),
                             sender=settings.DEFAULT_SENDER)

        log.debug('Sent')

        if not result[0]:
            return { 'code': Form.STATUS_CONFIRMATION_FAILED }


        # create the form in the database and mark the email confirmation as sent
        form = form or Form(email, host)
        form.confirm_sent = True
        DB.session.add(form)
        DB.session.commit()

        return { 'code': Form.STATUS_CONFIRMATION_SENT }

    @staticmethod
    def confirm(nonce):
        form = Form.query.filter_by(hash=nonce).first()
        if form:
            form.confirmed = True
            DB.session.add(form)
            DB.session.commit()
        return form
