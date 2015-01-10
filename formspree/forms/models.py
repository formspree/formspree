'''
database and its structure

'''
from formspree.app import DB
from formspree import settings, log
from flask import url_for, render_template
from helpers import HASH, http_form_to_dict, referrer_to_path, send_email
import datetime

class Form(DB.Model):
    __tablename__ = 'forms'

    id = DB.Column(DB.Integer, primary_key=True)
    hash = DB.Column(DB.String(32), unique=True)
    email = DB.Column(DB.String(120))
    host = DB.Column(DB.String(300))
    confirm_sent = DB.Column(DB.Boolean)
    confirmed = DB.Column(DB.Boolean)
    counter = DB.Column(DB.Integer)

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

        if not spam:
            now = datetime.datetime.utcnow().strftime('%I:%M %p UTC - %d %B %Y')
            text = render_template('email/form.txt', data=data, host=self.host, keys=keys, now=now)
            html = render_template('email/form.html', data=data, host=self.host, keys=keys, now=now)
            result = send_email(to=self.email,
                              subject=subject,
                              text=text,
                              html=html,
                              sender=settings.DEFAULT_SENDER,
                              reply_to=reply_to,
                              cc=cc)

            if not result[0]:
                return{ 'code': Form.STATUS_EMAIL_FAILED }

            # increment the forms counter
            self.counter = self.counter + 1
            DB.session.add(self)
            DB.session.commit()

        return { 'code': Form.STATUS_EMAIL_SENT, 'next': next }

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
