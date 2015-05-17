import httpretty
import json
import stripe

from formspree import settings
from formspree.app import DB
from formspree.forms.helpers import HASH
from formspree.users.models import User, Email
from formspree.forms.models import Form

from formspree_test_case import FormspreeTestCase
from utils import parse_confirmation_link_sent

class UserAccountsTestCase(FormspreeTestCase):

    @httpretty.activate
    def test_user_auth(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        # register
        r = self.client.post('/register',
            data={'email': 'alice@springs.com',
                  'password': 'canada'}
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.location.endswith('/account'))
        self.assertEqual(1, User.query.count())

        # email confirmation
        user = User.query.filter_by(email='alice@springs.com').first()
        self.assertIsNone(Email.query.get(['alice@springs.com', user.id]))

        link, qs = parse_confirmation_link_sent(httpretty.last_request().body)
        self.client.get(
            link,
            query_string=qs,
            follow_redirects=True
        )
        email = Email.query.get(['alice@springs.com', user.id])
        self.assertEqual(Email.query.count(), 1)
        self.assertIsNotNone(email)
        self.assertEqual(email.owner_id, user.id)

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

    def test_user_upgrade_and_downgrade(self):
        # check correct usage of stripe test keys during test
        self.assertIn('_test_', settings.STRIPE_PUBLISHABLE_KEY)
        self.assertIn('_test_', settings.STRIPE_SECRET_KEY)
        self.assertIn(stripe.api_key, settings.STRIPE_TEST_SECRET_KEY)

        # register user
        r = self.client.post('/register',
            data={'email': 'maria@example.com',
                  'password': 'uva'}
        )
        self.assertEqual(r.status_code, 302)

        user = User.query.filter_by(email='maria@example.com').first()
        self.assertEqual(user.upgraded, False)
        
        # subscribe with card through stripe
        token = stripe.Token.create(card={
            'number': '4242424242424242',
            'exp_month': '11',
            'exp_year':'2026',
            'cvc': '123',
        })['id']
        r = self.client.post('/account/upgrade', data={
            'stripeToken': token
        })

        user = User.query.filter_by(email='maria@example.com').first()
        self.assertEqual(user.upgraded, True)

        # downgrade back to the free plan
        r = self.client.post('/account/downgrade', follow_redirects=True)

        # redirect back to /account, the HTML shows that the user is not yet
        # in the free plan, since it will be valid for the next 30 days
        self.assertIn('<form action="/account/downgrade" method="POST">', r.data)

        user = User.query.filter_by(email='maria@example.com').first()
        self.assertEqual(user.upgraded, True)

        customer = stripe.Customer.retrieve(user.stripe_id)
        self.assertEqual(customer.subscriptions.data[0].cancel_at_period_end, True)

        # simulate stripe webhook reporting that the plan has been canceled just now
        customer.subscriptions.data[0].delete()
        # this will send webhooks automatically only for 
        # endpoints registered on the stripe dashboard

        self.client.post('/webhooks/stripe', data=json.dumps({
            'type': 'customer.subscription.deleted',
            'data': {
                'object': {
                    'customer': user.stripe_id
                }
            }
        }), headers={'Content-type': 'application/json'})

        user = User.query.filter_by(email='maria@example.com').first()
        self.assertEqual(user.upgraded, False)

        # delete the stripe customer
        customer.delete()


