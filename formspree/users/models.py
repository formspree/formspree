import hmac
import hashlib
from datetime import datetime
from flask import url_for, render_template, g

from formspree import settings
from formspree.utils import send_email, IS_VALID_EMAIL
from formspree.app import DB
from helpers import hash_pwd

class User(DB.Model):
    __tablename__ = 'users'

    id = DB.Column(DB.Integer, primary_key=True)
    email = DB.Column(DB.Text, unique=True, index=True)
    password = DB.Column(DB.String(100))
    upgraded = DB.Column(DB.Boolean)
    stripe_id = DB.Column(DB.String(50))
    registered_on = DB.Column(DB.DateTime)
    invoice_address = DB.Column(DB.Text)

    emails = DB.relationship('Email', backref='owner', lazy='dynamic')

    @property
    def forms(self):
        from formspree.forms.models import Form
        by_email = DB.session.query(Form) \
            .join(Email, Email.address == Form.email) \
            .join(User, User.id == Email.owner_id) \
            .filter(User.id == self.id)
        by_creation = DB.session.query(Form) \
            .join(User, User.id == Form.owner_id) \
            .filter(User.id == self.id)
        return by_creation.union(by_email)

    def __init__(self, email, password):
        email = email.lower().strip()
        if not IS_VALID_EMAIL(email):
            raise ValueError('Cannot create User. %s is not a valid email.' % email)

        self.email = email
        self.password = hash_pwd(password)
        self.upgraded = False
        self.registered_on = datetime.utcnow()

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def reset_password_digest(self):
        return hmac.new(
            settings.NONCE_SECRET,
            'id={0}&password={1}'.format(self.id, self.password),
            hashlib.sha256
        ).hexdigest()

    def send_password_reset(self):
        g.log.info('Sending password reset.', account=self.email)

        digest = self.reset_password_digest()
        link = url_for('reset-password', digest=digest, email=self.email, _external=True)
        res = send_email(
            to=self.email,
            subject='Reset your %s password!' % settings.SERVICE_NAME,
            text=render_template('email/reset-password.txt', addr=self.email, link=link),
            html=render_template('email/reset-password.html', add=self.email, link=link),
            sender=settings.ACCOUNT_SENDER
        )
        if not res[0]:
            g.log.info('Failed to send email.', reason=res[1], code=res[2])
            return False
        else:
            return True

    @classmethod
    def from_password_reset(cls, email, digest):
        user = User.query.filter_by(email=email).first()
        if not user: return None

        what_should_be = user.reset_password_digest()
        if digest == what_should_be:
            return user
        else:
            return None


class Email(DB.Model):
    __tablename__ = 'emails'

    """
    emails added here are already confirmed and can be trusted.
    """

    address = DB.Column(DB.Text, primary_key=True)
    owner_id = DB.Column(DB.Integer, DB.ForeignKey('users.id'), primary_key=True)
    registered_on = DB.Column(DB.DateTime, default=DB.func.now())

    @staticmethod
    def send_confirmation(addr, user_id):
        g.log = g.log.new(address=addr, user_id=user_id)
        g.log.info('Sending email confirmation for new address on account.')

        addr = addr.lower().strip()
        if not IS_VALID_EMAIL(addr):
            g.log.info('Failed. Invalid address.')
            raise ValueError(u'Cannot send confirmation. '
                             '{} is not a valid email.'.format(addr))

        message = u'email={email}&user_id={user_id}'.format(
            email=addr,
            user_id=user_id)
        digest = hmac.new(
            settings.NONCE_SECRET, message.encode('utf-8'), hashlib.sha256
        ).hexdigest()
        link = url_for('confirm-account-email',
                       digest=digest, email=addr, _external=True)
        res = send_email(
            to=addr,
            subject='Confirm email for your account at %s' % settings.SERVICE_NAME,
            text=render_template('email/confirm-account.txt', email=addr, link=link),
            html=render_template('email/confirm-account.html', email=addr, link=link),
            sender=settings.ACCOUNT_SENDER
        )
        if not res[0]:
            g.log.info('Failed to send email.', reason=res[1], code=res[2])
            return False
        else:
            return True

    @classmethod
    def create_with_digest(cls, addr, user_id, digest):
        addr = addr.lower()
        message = u'email={email}&user_id={user_id}'.format(
            email=addr,
            user_id=user_id)
        what_should_be = hmac.new(
            settings.NONCE_SECRET, message.encode('utf-8'), hashlib.sha256
        ).hexdigest()
        if digest == what_should_be:
            return cls(address=addr, owner_id=user_id)
        else:
            return None
