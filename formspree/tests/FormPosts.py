import os
import unittest
import httpretty


from formspree import create_app, app
from formspree.forms.models import Form

ajax_headers = {
    'Referer': 'example.com',
    'X_REQUESTED_WITH': 'xmlhttprequest'
}

class FormPostsTestCase(unittest.TestCase):

    def setUp(self):
        #create database here?
        Form.query.delete()
        self.app = create_app() # new app everytime?
        self.client = self.app.test_client()


    def tearDown(self):
        #destroy database here?
        Form.query.delete()
        c = Form.query.count()

    def test_index_page(self):
        r = self.client.get('/')
        self.assertEqual(200, r.status_code)

    @httpretty.activate
    def test_submit_form(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
        r = self.client.post('/alice@example.com',
            headers = ajax_headers,
            data={'name': 'alice'}
        )
        self.assertEqual(1, Form.query.count())

    @httpretty.activate
    def test_second_form(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
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


    @httpretty.activate    
    def test_activation_workflow(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
        r = self.client.post('/bob@example.com',
            headers = ajax_headers,
            data={'name': 'bob'}
        )
        f = Form.query.first()
        self.assertEqual(f.email, 'bob@example.com')
        self.assertEqual(f.host, 'example.com')
        self.assertEqual(f.confirm_sent, True)
        self.assertEqual(f.counter, 0)
        self.assertEqual(f.owner_id, None)

        # form has another submission, counter should increase?
        r = self.client.post('/bob@example.com',
            headers = ajax_headers,
            data={'name': 'bob'}
        )
        number_of_forms = Form.query.count()
        self.assertEqual(number_of_forms, 1) # still only one form

        # assert form data is still the same
        f = Form.query.first()
        self.assertEqual(f.email, 'bob@example.com')
        self.assertEqual(f.host, 'example.com')
        self.assertEqual(f.confirm_sent, True)
        self.assertEqual(f.counter, 0)
        self.assertEqual(f.owner_id, None)

        # test clicking of activation link
        self.client.get('/confirm/%s' % (f.hash,))

        f = Form.query.first()
        self.assertEqual(f.confirmed, True)

        # a third submission should now increase the counter
        r = self.client.post('/bob@example.com',
            headers = ajax_headers,
            data={'name': 'bob'}
        )
        number_of_forms = Form.query.count()
        self.assertEqual(number_of_forms, 1) # still only one form

        f = Form.query.first()
        self.assertEqual(f.email, 'bob@example.com')
        self.assertEqual(f.host, 'example.com')
        self.assertEqual(f.confirm_sent, True)
        self.assertEqual(f.owner_id, None)
        self.assertEqual(f.counter, 1) # counter has increased




