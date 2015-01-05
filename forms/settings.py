import os

# load a bunch of environment

DEBUG = os.getenv('DEBUG') in ['True', 'true', '1', 'yes']
if DEBUG:
    SQLALCHEMY_ECHO = True

NONCE_SECRET = os.getenv('NONCE_SECRET')
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')

REDIS_URL = os.getenv('REDISTOGO_URL') or os.getenv('REDISGREEN_URL') or 'http://localhost:6379'

SERVICE_NAME = os.getenv('SERVICE_NAME') or 'Forms'
SERVICE_URL = os.getenv('SERVICE_URL') or 'http://example.com'
CONTACT_EMAIL = os.getenv('CONTACT_EMAIL') or 'team@example.com'
DEFAULT_SENDER = os.getenv('DEFAULT_SENDER') or 'Forms Team <submissions@example.com>'
API_ROOT = os.getenv('API_ROOT') or '//example.com'

SENDGRID_USERNAME = os.getenv('SENDGRID_USERNAME')
SENDGRID_PASSWORD = os.getenv('SENDGRID_PASSWORD')
