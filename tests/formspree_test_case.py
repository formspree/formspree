
import os
import fakeredis

from flask.ext.testing import TestCase
import formspree
from formspree import create_app
from formspree import settings
from formspree.app import DB, REDIS


class FormspreeTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        ''' configures app for testing '''
        formspree.app.get_redis = lambda : fakeredis.FakeStrictRedis()
        settings.MONTHLY_SUBMISSIONS_LIMIT = 2
        settings.SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL')

    def create_app(self):        
        app = create_app()
        return app

    def setUp(self):
        self.assertNotEqual(settings.SQLALCHEMY_DATABASE_URI, os.getenv('DATABASE_URL'))
        self.assertEqual(type(REDIS()), fakeredis.FakeStrictRedis)
        self.tearDown()
        DB.create_all()

    def tearDown(self):
        DB.session.remove()
        DB.drop_all()
        REDIS().flushdb()