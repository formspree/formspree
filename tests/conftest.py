import os
import re
import time
import pytest
import redis
from urllib.parse import unquote
from unittest.mock import patch, DEFAULT

from formspree import settings
from formspree.create_app import create_app
from formspree.stuff import DB, redis_store, celery

@pytest.fixture
def worker():
    return BurstWorker()

@pytest.fixture
def msend():
    with patch('formspree.utils.send_email') as msend:
        def side_effect(*args, **kwargs):
            msend(*args, **kwargs)
            return DEFAULT

        with \
              patch('formspree.users.models.send_email', side_effect=side_effect), \
              patch('formspree.users.views.send_email', side_effect=side_effect), \
              patch('formspree.users.helpers.send_email', side_effect=side_effect), \
              patch('formspree.forms.models.send_email', side_effect=side_effect), \
              patch('formspree.forms.views.send_email', side_effect=side_effect):
            yield msend

@pytest.fixture
def app():
    settings.MONTHLY_SUBMISSIONS_LIMIT = 2
    settings.ARCHIVED_SUBMISSIONS_LIMIT = 2
    settings.OVERLIMIT_NOTIFICATION_QUANTITY = 2
    settings.FORM_LIMIT_DECREASE_ACTIVATION_SEQUENCE = 0
    settings.EXPENSIVELY_WIPE_SUBMISSIONS_FREQUENCY = 1
    settings.PRESERVE_CONTEXT_ON_EXCEPTION = False
    settings.SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL')
    settings.STRIPE_PUBLISHABLE_KEY = settings.STRIPE_TEST_PUBLISHABLE_KEY
    settings.STRIPE_SECRET_KEY = settings.STRIPE_TEST_SECRET_KEY
    settings.PRESERVE_CONTEXT_ON_EXCEPTION = False
    settings.TESTING = True
    return create_app()

@pytest.fixture()
def client(app):
    assert settings.SQLALCHEMY_DATABASE_URI != os.getenv('DATABASE_URL')

    with app.app_context():
        DB.create_all()

        with app.test_request_context():
            yield app.test_client()

        DB.session.remove()
        DB.drop_all()

    redis_store.flushdb()

def parse_confirmation_link_sent(email_text):
    matchlink = re.search('Link: ([^?]+)\?(\S+)', email_text)
    if not matchlink:
        raise ValueError('No link found in email body:', email_text)

    link = matchlink.group(1)
    qs = matchlink.group(2)

    return link, qs
