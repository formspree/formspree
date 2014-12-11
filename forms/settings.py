import os

# load a bunch of environment

DEBUG = os.getenv('DEBUG') in ['True', 'true', '1', 'yes']

#SERVER_NAME = os.getenv('SERVER_NAME')
NONCE_SECRET = os.getenv('NONCE_SECRET')
REDIS_URL = os.getenv('REDISTOGO_URL') or os.getenv('REDISGREEN_URL') or 'http://localhost:6379'
MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')
MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN')

SERVICE_NAME = os.getenv('SERVICE_NAME') or 'Forms'
SERVICE_URL = os.getenv('SERVICE_URL') or 'http://myapp.com'
CONTACT_EMAIL = os.getenv('CONTACT_EMAIL') or 'team@myapp.com'
DEFAULT_SENDER = os.getenv('DEFAULT_SENDER') or 'Forms Team <submissions@myapp.com>'
API_ROOT = os.getenv('API_ROOT') or '//api.myapp.com'