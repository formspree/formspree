import os
import unittest

from formspree import create_app, app
from formspree.forms.models import Form

ajax_headers = {
    'Referer': 'example.com',
    'X_REQUESTED_WITH': 'xmlhttprequest'
}

class FormPostsTestCase(unittest.TestCase):

    def setUp(self):
        #create database here?
        self.app = create_app() # new app everytime?
        self.client = self.app.test_client()


    def tearDown(self):
        #destroy database here?
        Form.query.delete()
        c = Form.query.count()
        print 'Torn down. %s left.' % c #TODO: this always says 0, but there is still a row left in the database

    def test_index_page(self):
        r = self.client.get('/')
        self.assertEqual(200, r.status_code)

    def test_submit_form(self):
        r = self.client.post('/alice@example.com',
            headers = ajax_headers,
            data={'name': 'alice'}
        )
        self.assertEqual(1, Form.query.count())

    def test_second_form(self):
        r = self.client.post('/bob@example.com',
            headers = ajax_headers,
            data={'name': 'bob'}
        )
        self.assertEqual(1, Form.query.count())

    def test_fail_form_submission(self):
        no_referer = ajax_headers.copy()
        del no_referer['Referer']
        r = self.client.post('/bob@example.com',
            headers = no_referer,
            data={'name': 'bob'}
        )
        self.assertNotEqual(200, r.status_code)


