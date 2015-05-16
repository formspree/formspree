import hmac
import hashlib
from datetime import datetime
from flask import url_for, render_template

from formspree import settings
from formspree.utils import send_email, IS_VALID_EMAIL
from formspree.app import DB
from formspree.forms.models import Form
from helpers import hash_pwd

class User(DB.Model):
    __tablename__ = 'users'

    id = DB.Column(DB.Integer, primary_key=True)
    email = DB.Column(DB.Text, unique=True, index=True)
    password = DB.Column(DB.String(100))
    upgraded = DB.Column(DB.Boolean)
    stripe_id = DB.Column(DB.String(50))
    registered_on = DB.Column(DB.DateTime)

    emails = DB.relationship('Email', backref='owner', lazy='dynamic')

    @property
    def forms(self):
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

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

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
        addr = addr.lower().strip()
        if not IS_VALID_EMAIL(addr):
            raise ValueError('Cannot send confirmation. %s is not a valid email.' % addr)

        message = 'email={email}&user_id={user_id}'.format(email=addr, user_id=user_id)
        digest = hmac.new(settings.NONCE_SECRET, message, hashlib.sha256).hexdigest()
        link = url_for('confirm-account-email', digest=digest, email=addr, _external=True)
        res = send_email(
            to=addr,
            subject='Confirm email for your account at %s' % settings.SERVICE_NAME,
            text=render_template('email/confirm-account.txt', email=addr, link=link),
            html=render_template('email/confirm-account.html', email=addr, link=link),
            sender=settings.ACCOUNT_SENDER
        )
        if not res[0]:
            return False
        else:
            return True

    @classmethod
    def create_with_digest(cls, addr, user_id, digest):
        addr = addr.lower()
        message = 'email={email}&user_id={user_id}'.format(email=addr, user_id=user_id)
        what_should_be = hmac.new(settings.NONCE_SECRET, message, hashlib.sha256).hexdigest()
        if digest == what_should_be:
            return cls(address=addr, owner_id=user_id)
        else:
            return None
