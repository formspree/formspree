import os
import sys

# load a bunch of environment

DEBUG = os.getenv('DEBUG') in ['True', 'true', '1', 'yes']
if DEBUG:
    SQLALCHEMY_ECHO = True
TESTING = os.getenv('TESTING') in ['True', 'true', '1', 'yes']

SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')

LOG_LEVEL = os.getenv('LOG_LEVEL') or 'debug'

SECRET_KEY = os.getenv('SECRET_KEY')
NONCE_SECRET = os.getenv('NONCE_SECRET')
HASHIDS_SALT = os.getenv('HASHIDS_SALT')

MONTHLY_SUBMISSIONS_LIMIT = int(os.getenv('MONTHLY_SUBMISSIONS_LIMIT') or 1000)
ARCHIVED_SUBMISSIONS_LIMIT = int(os.getenv('ARCHIVED_SUBMISSIONS_LIMIT') or 100)
REDIS_URL = os.getenv('REDISTOGO_URL') or os.getenv('REDISCLOUD_URL')

CDN_URL = os.getenv('CDN_URL')

SERVICE_NAME = os.getenv('SERVICE_NAME') or 'Forms'
UPGRADED_PLAN_NAME = os.getenv('UPGRADED_PLAN_NAME') or 'Gold'
SERVICE_URL = os.getenv('SERVICE_URL') or 'http://example.com'
CONTACT_EMAIL = os.getenv('CONTACT_EMAIL') or 'team@example.com'
DEFAULT_SENDER = os.getenv('DEFAULT_SENDER') or 'Forms Team <submissions@example.com>'
ACCOUNT_SENDER = os.getenv('ACCOUNT_SENDER') or DEFAULT_SENDER
API_ROOT = os.getenv('API_ROOT') or '//example.com'

SENDGRID_USERNAME = os.getenv('SENDGRID_USERNAME')
SENDGRID_PASSWORD = os.getenv('SENDGRID_PASSWORD')

STRIPE_TEST_PUBLISHABLE_KEY = os.getenv('STRIPE_TEST_PUBLISHABLE_KEY')
STRIPE_TEST_SECRET_KEY = os.getenv('STRIPE_TEST_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY') or STRIPE_TEST_PUBLISHABLE_KEY
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY') or STRIPE_TEST_SECRET_KEY

RECAPTCHA_SECRET = os.getenv('RECAPTCHA_SECRET')
RECAPTCHA_KEY = os.getenv('RECAPTCHA_KEY')

RATE_LIMIT = os.getenv('RATE_LIMIT', '30 per hour')
REDIS_RATE_LIMIT = os.getenv('REDIS_URL')  # heroku-redis

CONTACT_FORM_HASHID = os.getenv('CONTACT_FORM_HASHID', CONTACT_EMAIL)

TYPEKIT_KEY = os.getenv('TYPEKIT_KEY', '1234567')
