# encoding: utf-8

import httpretty
import json

from formspree import settings
from formspree.app import DB
from formspree.forms.helpers import HASH
from formspree.users.models import User, Email
from formspree.forms.models import Form, Submission

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
            headers={'Referer': 'http://testsite.com'},
            data={'name': 'bruce'}
        )
        self.assertIn("sent an email confirmation", r.data)
        self.assertIn('confirm+your+email', httpretty.last_request().body)
        self.assertEqual(1, Form.query.count())

        # confirm form
        form = Form.query.first()
        self.client.get('/confirm/%s:%s' % (HASH(form.email, str(form.id)), form.hashid))
        self.assertTrue(Form.query.first().confirmed)

        # Make sure that it marks the first form as AJAX
        self.assertTrue(Form.query.first().uses_ajax)

        # check captcha disabling
        self.assertFalse(Form.query.first().captcha_disabled)
        r = self.client.get('/forms/' + form_endpoint + '/toggle-recaptcha',
            headers={'Referer': settings.SERVICE_URL})
        self.assertTrue(Form.query.first().captcha_disabled)
        r = self.client.get('/forms/' + form_endpoint + '/toggle-recaptcha',
            headers={'Referer': settings.SERVICE_URL})
        self.assertFalse(Form.query.first().captcha_disabled)


        # send 5 forms (monthly limits should not apply to the upgraded user)
        self.assertEqual(settings.MONTHLY_SUBMISSIONS_LIMIT, 2)
        for i in range(5):
            r = self.client.post('/' + form_endpoint,
                headers={'Referer': 'testsite.com'},
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
    def test_form_creation_with_a_registered_email(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        # register user
        r = self.client.post('/register',
            data={'email': 'user@testsite.com',
                  'password': 'banana'}
        )
        # upgrade user manually
        user = User.query.filter_by(email='user@testsite.com').first()
        user.upgraded = True
        DB.session.add(user)
        DB.session.commit()

        httpretty.reset()
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        # create form without providing an url should not send verification email
        r = self.client.post('/forms',
            headers={'Accept': 'application/json', 'Content-type': 'application/json'},
            data=json.dumps({'email': 'email@testsite.com'})
        )
        self.assertEqual(httpretty.has_request(), False)

        # create form without a confirmed email should send a verification email
        r = self.client.post('/forms',
            headers={'Accept': 'application/json', 'Content-type': 'application/json'},
            data=json.dumps({'email': 'email@testsite.com',
                             'url': 'https://www.testsite.com/contact.html'})
        )
        resp = json.loads(r.data)
        self.assertEqual(resp['confirmed'], False)
        self.assertEqual(httpretty.has_request(), True)
        self.assertIn('Confirm+email', httpretty.last_request().body)
        self.assertIn('www.testsite.com%2Fcontact.html', httpretty.last_request().body)

        # manually verify an email
        email = Email()
        email.address = 'owned-by@testsite.com'
        email.owner_id = user.id
        DB.session.add(email)
        DB.session.commit()

        # create a form with the verified email address
        r = self.client.post('/forms',
            headers={'Accept': 'application/json', 'Content-type': 'application/json'},
            data=json.dumps({'email': 'owned-by@testsite.com',
                             'url': 'https://www.testsite.com/about.html'})
        )
        resp = json.loads(r.data)
        self.assertEqual(resp['confirmed'], True)
        self.assertIn('www.testsite.com%2Fcontact.html', httpretty.last_request().body) # same as the last, means no new request was made

        # should have three created forms in the end
        self.assertEqual(Form.query.count(), 3)

    @httpretty.activate
    def test_sitewide_forms(self):
        httpretty.register_uri(httpretty.GET,
                               'http://mysite.com/formspree-verify.txt',
                               body=u'other_email@forms.com\nmyüñìćõð€email@email.com',
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               'http://www.naive.com/formspree-verify.txt',
                               body=u'myüñìćõð€email@email.com',
                               status=200)

        # register user
        r = self.client.post('/register',
            data={'email': 'user@testsite.com',
                  'password': 'banana'}
        )
        # upgrade user manually
        user = User.query.filter_by(email='user@testsite.com').first()
        user.upgraded = True
        DB.session.add(user)
        DB.session.commit()

        # manually verify an email
        email = Email()
        email.address = u'myüñìćõð€email@email.com'
        email.owner_id = user.id
        DB.session.add(email)
        DB.session.commit()

        # create a sitewide form with the verified email address
        r = self.client.post('/forms',
            headers={'Accept': 'application/json', 'Content-type': 'application/json'},
            data=json.dumps({'email': u'myüñìćõð€email@email.com',
                             'url': 'http://mysite.com',
                             'sitewide': 'true'})
        )
        resp = json.loads(r.data)

        self.assertEqual(httpretty.has_request(), True)
        self.assertEqual(resp['confirmed'], True)

        self.assertEqual(1, Form.query.count())
        forms = Form.query.all()
        form = forms[0]
        self.assertEqual(form.sitewide, True)
        self.assertEqual(form.host, 'mysite.com')

        # submit form
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        r = self.client.post('/' + form.hashid,
            headers = {'Referer': 'http://www.mysite.com/hipopotamo', 'content-type': 'application/json'},
            data=json.dumps({'name': 'alice'})
        )
        self.assertIn('alice', httpretty.last_request().body)

        self.client.post('/' + form.hashid,
            headers = {'Referer': 'http://mysite.com/baleia/urso?w=2', 'content-type': 'application/json'},
            data=json.dumps({'name': 'maria'})
        )
        self.assertIn('maria', httpretty.last_request().body)

        self.client.post('/' + form.hashid,
            headers = {'Referer': 'http://mysite.com/', 'content-type': 'application/json'},
            data=json.dumps({'name': 'laura'})
        )
        self.assertIn('laura', httpretty.last_request().body)

        # another form, now with a www prefix that will be stripped
        r = self.client.post('/forms',
            headers={'Accept': 'application/json', 'Content-type': 'application/json'},
            data=json.dumps({'email': u'myüñìćõð€email@email.com',
                             'url': 'http://www.naive.com',
                             'sitewide': 'true'})
        )
        resp = json.loads(r.data)

        self.assertEqual(httpretty.has_request(), True)
        self.assertEqual(resp['confirmed'], True)

        self.assertEqual(2, Form.query.count())
        forms = Form.query.all()
        form = forms[1]
        self.assertEqual(form.sitewide, True)
        self.assertEqual(form.host, 'naive.com')

        # submit form
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        r = self.client.post('/' + form.hashid,
            headers={'Referer': 'http://naive.com/hipopotamo', 'content-type': 'application/json'},
            data=json.dumps({'name': 'alice'})
        )
        self.assertIn('alice', httpretty.last_request().body)

        self.client.post('/' + form.hashid,
            headers={'Referer': 'http://www.naive.com/baleia/urso?w=2', 'content-type': 'application/json'},
            data=json.dumps({'name': 'maria'})
        )
        self.assertIn('maria', httpretty.last_request().body)

        self.client.post('/' + form.hashid,
            headers={'Referer': 'http://www.naive.com/', 'content-type': 'application/json'},
            data=json.dumps({'name': 'laura'})
        )
        self.assertIn('laura', httpretty.last_request().body)

        # create a different form with the same email address, now using unprefixed url
        r = self.client.post('/forms',
            headers={'Accept': 'application/json', 'Content-type': 'application/json'},
            data=json.dumps({'email': u'myüñìćõð€email@email.com',
                             'url': 'mysite.com',
                             'sitewide': 'true'})
        )
        resp = json.loads(r.data)
