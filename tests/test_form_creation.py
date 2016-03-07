import httpretty
import json

from formspree import settings
from formspree.app import DB
from formspree.forms.helpers import HASH
from formspree.users.models import User, Email
from formspree.forms.models import Form

from formspree_test_case import FormspreeTestCase
from utils import parse_confirmation_link_sent

class TestFormCreationFromDashboard(FormspreeTestCase):

    @httpretty.activate
    def test_form_creation(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        # register user
        r = self.client.post('/register',
            data={'email': 'colorado@springs.com',
                  'password': 'banana'}
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(1, User.query.count())

        # fail to create form
        r = self.client.post('/forms',
            headers={'Content-type': 'application/json'},
            data={'email': 'hope@springs.com'}
        )
        self.assertEqual(r.status_code, 402)
        self.assertIn('error', json.loads(r.data))
        self.assertEqual(0, Form.query.count())

        # upgrade user manually
        user = User.query.filter_by(email='colorado@springs.com').first()
        user.upgraded = True
        DB.session.add(user)
        DB.session.commit()

        # successfully create form
        r = self.client.post('/forms',
            headers={'Accept': 'application/json', 'Content-type': 'application/json'},
            data=json.dumps({'email': 'hope@springs.com'})
        )
        resp = json.loads(r.data)
        self.assertEqual(r.status_code, 200)
        self.assertIn('submission_url', resp)
        self.assertIn('hashid', resp)
        form_endpoint = resp['hashid']
        self.assertIn(resp['hashid'], resp['submission_url'])
        self.assertEqual(1, Form.query.count())
        self.assertEqual(Form.query.first().id, Form.get_with_hashid(resp['hashid']).id)

        # post to form
        r = self.client.post('/' + form_endpoint,
            headers={'Referer': 'formspree.io'},
            data={'name': 'bruce'}
        )
        self.assertIn("We've sent a link to your email", r.data)
        self.assertIn('confirm+your+email', httpretty.last_request().body)
        self.assertEqual(1, Form.query.count())

        # confirm form
        form = Form.query.first()
        self.client.get('/confirm/%s:%s' % (HASH(form.email, str(form.id)), form.hashid))
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

    @httpretty.activate
    def test_form_creation_without_a_registered_email(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        # register user
        r = self.client.post('/register',
            data={'email': 'user@formspree.io',
                  'password': 'banana'}
        )
        # upgrade user manually
        user = User.query.filter_by(email='user@formspree.io').first()
        user.upgraded = True
        DB.session.add(user)
        DB.session.commit()

        # create form without providing an url should not send verification email
        httpretty.reset()
        r = self.client.post('/forms',
            headers={'Accept': 'application/json', 'Content-type': 'application/json'},
            data=json.dumps({'email': 'email@formspree.io'})
        )
        self.assertEqual(httpretty.has_request(), False)

        # create form without a confirmed email should send a verification email
        httpretty.reset()
        r = self.client.post('/forms',
            headers={'Accept': 'application/json', 'Content-type': 'application/json'},
            data=json.dumps({'email': 'email@formspree.io',
                             'url': 'https://www.testsite.com/contact.html'})
        )
        resp = json.loads(r.data)
        self.assertEqual(resp['confirmed'], False)
        self.assertEqual(httpretty.has_request(), True)
        self.assertIn('Confirm+email', httpretty.last_request().body)
        self.assertIn('www.testsite.com%2Fcontact.html', httpretty.last_request().body)

        # manually verify an email
        email = Email()
        email.address = 'owned-by@formspree.io'
        email.owner_id = user.id
        DB.session.add(email)
        DB.session.commit()

        # create a form with the verified email address
        httpretty.reset()
        r = self.client.post('/forms',
            headers={'Accept': 'application/json', 'Content-type': 'application/json'},
            data=json.dumps({'email': 'owned-by@formspree.io',
                             'url': 'https://www.testsite.com/about.html'})
        )
        resp = json.loads(r.data)
        self.assertEqual(resp['confirmed'], True)
        self.assertEqual(httpretty.has_request(), False)

        # should have three created forms in the end
        self.assertEqual(Form.query.count(), 3)
