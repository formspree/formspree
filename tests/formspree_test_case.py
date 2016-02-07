
import os
import fakeredis

from flask.ext.testing import TestCase
import mock
import formspree
from formspree import create_app
from formspree import settings
from formspree.app import DB, redis_store


class FormspreeTestCase(TestCase):
    def create_app(self):
        self.redis_patcher = mock.patch('flask_redis.RedisClass', new_callable=fakeredis.FakeStrictRedis)
        self.redis_patcher.start()

        settings.MONTHLY_SUBMISSIONS_LIMIT = 2
        settings.ARCHIVED_SUBMISSIONS_LIMIT = 2
        settings.PRESERVE_CONTEXT_ON_EXCEPTION = False
        settings.SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL')

        settings.PRESERVE_CONTEXT_ON_EXCEPTION = False

        settings.PRESERVE_CONTEXT_ON_EXCEPTION = False

        return create_app()

    def setUp(self):
        self.assertNotEqual(settings.SQLALCHEMY_DATABASE_URI, os.getenv('DATABASE_URL'))
        self.assertIsInstance(redis_store.connection, fakeredis.FakeStrictRedis)

        DB.create_all()

        super(FormspreeTestCase, self).setUp()

    def tearDown(self):
        DB.session.remove()
        DB.drop_all()
        redis_store.flushdb()

        self.redis_patcher.stop()

        super(FormspreeTestCase, self).tearDown()
