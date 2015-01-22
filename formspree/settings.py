import os
import sys

# load a bunch of environment

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG') in ['True', 'true', '1', 'yes']
if DEBUG:
    SQLALCHEMY_ECHO = True

TESTING = True if 'test' in sys.argv else False
TEST_DATABASE = os.getenv('TEST_DATABASE_URL')
SQLALCHEMY_DATABASE_URI = TEST_DATABASE if TESTING else os.getenv('DATABASE_URL')

LOG_LEVEL = os.getenv('LOG_LEVEL') or 'debug'
NONCE_SECRET = os.getenv('NONCE_SECRET')

MONTHLY_SUBMISSIONS_LIMIT = 2 if TESTING else int(os.getenv('MONTHLY_SUBMISSIONS_LIMIT') or 1000)
REDIS_URL = os.getenv('REDISTOGO_URL')

SERVICE_NAME = os.getenv('SERVICE_NAME') or 'Forms'
SERVICE_URL = os.getenv('SERVICE_URL') or 'http://example.com'
CONTACT_EMAIL = os.getenv('CONTACT_EMAIL') or 'team@example.com'
DEFAULT_SENDER = os.getenv('DEFAULT_SENDER') or 'Forms Team <submissions@example.com>'
API_ROOT = os.getenv('API_ROOT') or '//example.com'

SENDGRID_USERNAME = os.getenv('SENDGRID_USERNAME')
SENDGRID_PASSWORD = os.getenv('SENDGRID_PASSWORD')
