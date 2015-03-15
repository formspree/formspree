from formspree.app import DB
from helpers import hash_pwd
from datetime import datetime

class User(DB.Model):
    __tablename__ = 'users'

    id = DB.Column(DB.Integer , primary_key=True)
    email = DB.Column(DB.String(50),unique=True , index=True)
    password = DB.Column(DB.String(100))
    upgraded = DB.Column(DB.Boolean)
    stripe_id = DB.Column(DB.String(50))
    registered_on = DB.Column(DB.DateTime)
    forms = DB.relationship('Form', backref='owner', lazy='dynamic')

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
