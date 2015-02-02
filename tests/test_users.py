import httpretty
import json

from formspree import settings
from formspree.app import DB
from formspree.forms.helpers import HASH
from formspree.users.models import User
from formspree.forms.models import Form

from formspree_test_case import FormspreeTestCase

class FormPostsTestCase(FormspreeTestCase):

    def test_user_auth(self):
        # register
        r = self.client.post('/register',
            data={'email': 'alice@springs.com',
                  'password': 'canada'}
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.location.endswith('/dashboard'))
        self.assertEqual(1, User.query.count())

        # logout
        r = self.client.get('/logout')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(1, User.query.count())

        # login   
        r = self.client.post('/login',
            data={'email': 'alice@springs.com',
                  'password': 'canada'}
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.location.endswith('/dashboard'))
        self.assertEqual(1, User.query.count())

    @httpretty.activate
    def test_form_creation(self):
        # register user
        r = self.client.post('/register',
            data={'email': 'colorado@springs.com',
                  'password': 'banana'}
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.location.endswith('/dashboard'), True)
        self.assertEqual(1, User.query.count())

        # fail to create form
        r = self.client.post('/forms',
            headers={'Content-type': 'application/json'},
            data={'email': 'hope@springs.com'}
        )
        self.assertEqual(r.status_code, 403)
        self.assertIn('error', json.loads(r.data))
        self.assertEqual(0, Form.query.count())

        # upgrade user manually
        user = User.query.filter_by(email='colorado@springs.com').first()
        user.upgraded = True
        DB.session.add(user)
        DB.session.commit()

        # successfully create form
        r = self.client.post('/forms',
            headers={'Content-type': 'application/json'},
            data=json.dumps({'email': 'hope@springs.com'})
        )
        resp = json.loads(r.data)
        self.assertEqual(r.status_code, 200)
        self.assertIn('submission_url', resp)
        self.assertIn('random_like_string', resp)
        form_endpoint = resp['random_like_string']
        self.assertIn(resp['random_like_string'], resp['submission_url'])
        self.assertEqual(1, Form.query.count())
        self.assertEqual(Form.query.first().id, Form.get_form_by_random_like_string(resp['random_like_string']).id)

        # post to form
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        r = self.client.post('/' + form_endpoint,
            headers={'Referer': 'formspree.io'},
            data={'name': 'bruce'}
        )
        self.assertIn("We've sent a link to your email", r.data)
        self.assertIn('confirm+your+email', httpretty.last_request().body)
        self.assertEqual(1, Form.query.count())

        # confirm form
        form = Form.query.first()
        self.client.get('/confirm/%s:%s' % (HASH(form.email, str(form.id)), form.id))
        self.assertTrue(Form.query.first().confirmed)

        # send 5 forms (monthly limits should not apply to the upgraded user)
        self.assertEqual(settings.MONTHLY_SUBMISSIONS_LIMIT, 2)
        for i in range(5):
            r = self.client.post('/' + form_endpoint,
                headers={'Referer': 'formspree.io'},
                data={'name': 'ana',
                      'submission': '__%s__' % i}
            )
        form = Form.query.first()
        self.assertEqual(form.counter, 5)
        self.assertEqual(form.get_monthly_counter(), 5)
        self.assertIn('ana', httpretty.last_request().body)
        self.assertIn('__4__', httpretty.last_request().body)
        self.assertNotIn('You+are+past+our+limit', httpretty.last_request().body)

        # try (and fail) to submit from a different host
        r = self.client.post('/' + form_endpoint,
            headers={'Referer': 'bad.com'},
            data={'name': 'usurper'}
        )
        self.assertEqual(r.status_code, 403)
        self.assertIn('ana', httpretty.last_request().body) # no more data is sent to sendgrid
        self.assertIn('__4__', httpretty.last_request().body)
