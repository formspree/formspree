import os
import unittest
import httpretty

from formspree import create_app, app
from formspree import settings
from formspree.app import DB, REDIS
from formspree.forms.models import Form

ajax_headers = {
    'Referer': 'example.com',
    'X_REQUESTED_WITH': 'xmlhttprequest'
}

test_app = create_app()
client = test_app.test_client()

class FormPostsTestCase(unittest.TestCase):

    def setUp(self):
        self.tearDown()
        DB.create_all()

    def tearDown(self):
        DB.session.remove()
        DB.drop_all()
        REDIS.flushdb()

    def test_index_page(self):
        r = client.get('/')
        self.assertEqual(200, r.status_code)

    @httpretty.activate
    def test_submit_form(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
        r = client.post('/alice@example.com',
            headers = ajax_headers,
            data={'name': 'alice'}
        )
        self.assertEqual(1, Form.query.count())

    @httpretty.activate
    def test_second_form(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
        r = client.post('/bob@example.com',
            headers = ajax_headers,
            data={'name': 'bob'}
        )
        self.assertEqual(1, Form.query.count())

    def test_fail_form_submission(self):
        no_referer = ajax_headers.copy()
        del no_referer['Referer']
        r = client.post('/bob@example.com',
            headers = no_referer,
            data={'name': 'bob'}
        )
        self.assertNotEqual(200, r.status_code)

    @httpretty.activate    
    def test_activation_workflow(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
        r = client.post('/bob@example.com',
            headers = ajax_headers,
            data={'name': 'bob'}
        )
        f = Form.query.first()
        self.assertEqual(f.email, 'bob@example.com')
        self.assertEqual(f.host, 'example.com')
        self.assertEqual(f.confirm_sent, True)
        self.assertEqual(f.counter, 0) # the counter shows zero submissions
        self.assertEqual(f.owner_id, None)
        self.assertEqual(f.get_monthly_counter(), 0) # monthly submissions also 0

        # form has another submission, number of forms in the table should increase?
        r = client.post('/bob@example.com',
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
        self.assertEqual(f.counter, 0) # still zero submissions
        self.assertEqual(f.owner_id, None)

        # test clicking of activation link
        client.get('/confirm/%s' % (f.hash,))

        f = Form.query.first()
        self.assertEqual(f.confirmed, True)

        # a third submission should now increase the counter
        r = client.post('/bob@example.com',
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
        self.assertEqual(f.get_monthly_counter(), 1) # monthly submissions also

    @httpretty.activate
    def test_monthly_limits(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        # monthly limit is set to 2 during tests
        self.assertEqual(settings.MONTHLY_SUBMISSIONS_LIMIT, 2)

        # manually verify luke@example.com
        r = client.post('/luke@example.com',
            headers = ajax_headers,
            data={'name': 'luke'}
        )
        f = Form.query.first()
        f.confirm_sent = True
        f.confirmed = True
        DB.session.add(f)
        DB.session.commit()

        # first submission
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
        r = client.post('/luke@example.com',
            headers = ajax_headers,
            data={'name': 'peter'}
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn('peter', httpretty.last_request().body)

        # second submission
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
        r = client.post('/luke@example.com',
            headers = ajax_headers,
            data={'name': 'ana'}
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn('ana', httpretty.last_request().body)

        # third submission, now we're over the limit
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
        r = client.post('/luke@example.com',
            headers = ajax_headers,
            data={'name': 'maria'}
        )
        self.assertEqual(r.status_code, 200) # the response to the user is the same
                                             # being the form over the limits or not

        # but the mocked sendgrid should never receive this last form
        self.assertNotIn('maria', httpretty.last_request().body)
        self.assertIn('You+are+past+our+limit', httpretty.last_request().body)

        # all the other variables are ok:
        self.assertEqual(1, Form.query.count())
        f = Form.query.first()
        self.assertEqual(f.counter, 3)
        self.assertEqual(f.get_monthly_counter(), 3) # the counters mark 4
