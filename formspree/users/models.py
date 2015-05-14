import hmac
import hashlib
from datetime import datetime
from flask import url_for, render_template

from formspree import settings
from formspree.utils import send_email
from formspree.app import DB
from helpers import hash_pwd

class User(DB.Model):
    __tablename__ = 'users'

    id = DB.Column(DB.Integer, primary_key=True)
    email = DB.Column(DB.String(50), unique=True, index=True)
    password = DB.Column(DB.String(100))
    upgraded = DB.Column(DB.Boolean)
    stripe_id = DB.Column(DB.String(50))
    registered_on = DB.Column(DB.DateTime)
    forms = DB.relationship('Form', backref='owner', lazy='dynamic')
    emails = DB.relationship('Email', backref='owner', lazy='dynamic')

    def __init__(self, email, password):
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
        addr = addr.lower()
        message = 'email={email}&user_id={user_id}'.format(email=addr, user_id=user_id)
        digest = hmac.new(settings.NONCE_SECRET, message, hashlib.sha256).hexdigest()
        link = url_for('confirm_account_email', digest=digest, email=addr, _external=True)
        res = send_email(to=addr,
                         subject='Confirm email for your account at %s' % settings.SERVICE_NAME,
                         text=render_template('email/confirm-account.txt', email=addr, link=link),
                         html=render_template('email/confirm-account.html', email=addr, link=link),
                         sender=settings.ACCOUNT_SENDER)
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
