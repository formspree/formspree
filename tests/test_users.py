import httpretty
import json
import stripe

from formspree import settings
from formspree.app import DB
from formspree.forms.helpers import HASH
from formspree.users.models import User, Email
from formspree.forms.models import Form, Submission

from formspree_test_case import FormspreeTestCase
from utils import parse_confirmation_link_sent

class UserAccountsTestCase(FormspreeTestCase):

    def test_register_page(self):
        r = self.client.get('/register')
        self.assertEqual(200, r.status_code)

    def test_login_page(self):
        r = self.client.get('/login')
        self.assertEqual(200, r.status_code)

    def test_forgot_password_page(self):
        r = self.client.get('/login/reset')
        self.assertEqual(200, r.status_code)

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
    def test_forgot_password(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        # register
        r = self.client.post('/register',
            data={'email': 'fragile@yes.com',
                  'password': 'roundabout'}
        )
        self.assertEqual(1, User.query.count())
        initial_password = User.query.all()[0].password

        # logout
        self.client.get('/logout')

        # forget password
        r = self.client.post('/login/reset',
            data={'email': 'fragile@yes.com'}
        )
        self.assertEqual(r.status_code, 200)

        # click on the email link
        link, qs = parse_confirmation_link_sent(httpretty.last_request().body)
        r = self.client.get(
            link,
            query_string=qs,
            follow_redirects=True
        )
        self.assertEqual(r.status_code, 200)

        # send new passwords (not matching)
        r = self.client.post(link, data={'password1': 'verdes', 'password2': 'roxas'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.location, link)
        self.assertEqual(User.query.all()[0].password, initial_password)

        # again, now matching
        r = self.client.post(link, data={'password1': 'amarelas', 'password2': 'amarelas'})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.location.endswith('/dashboard'))
        self.assertNotEqual(User.query.all()[0].password, initial_password)
        

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

    def test_form_toggle(self):
                # create and login a user
        r = self.client.post('/register',
            data={'email': 'hello@world.com',
                  'password': 'friend'}
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(1, User.query.count())

        # upgrade user
        user = User.query.filter_by(email='hello@world.com').first()
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

        # confirm form
        form = Form.query.first()
        self.client.get('/confirm/%s:%s' % (HASH(form.email, str(form.id)), form.hashid))
        self.assertTrue(Form.query.first().confirmed)
        self.assertEqual(0, Submission.query.count())

        # disable the form
        r = self.client.post('/forms/' + form_endpoint + '/toggle',
            headers={'Referer': settings.SERVICE_URL})
        self.assertEqual(302, r.status_code)
        self.assertTrue(r.location.endswith('/dashboard'))
        self.assertTrue(Form.query.first().disabled)
        self.assertEqual(0, Form.query.first().counter)

        # logout and attempt to enable the form
        self.client.get('/logout')
        r = self.client.post('/forms/' + form_endpoint + '/toggle',
            headers={'Referer': settings.SERVICE_URL},
            follow_redirects=True)
        self.assertEqual(200, r.status_code)
        self.assertTrue(Form.query.first().disabled)

        # fail when attempting to post to form
        r = self.client.post('/' + form_endpoint,
            headers={'Referer': 'formspree.io'},
            data={'name': 'bruce'}
        )
        self.assertEqual(403, r.status_code)
        self.assertEqual(0, Form.query.first().counter)

        # log back in and re-enable form
        r = self.client.post('/login',
            data={'email': 'hello@world.com',
                  'password': 'friend'}
        )
        r = self.client.post('/forms/' + form_endpoint + '/toggle',
            headers={'Referer': settings.SERVICE_URL},
            follow_redirects=True)
        self.assertEqual(200, r.status_code)
        self.assertFalse(Form.query.first().disabled)

        # successfully post to form
        r = self.client.post('/' + form_endpoint,
            headers={'Referer': 'formspree.io'},
            data={'name': 'bruce'}
        )
        self.assertEqual(1, Form.query.first().counter)

    def test_form_and_submission_deletion(self):
        # create and login a user
        r = self.client.post('/register',
            data={'email': 'hello@world.com',
                  'password': 'friend'}
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(1, User.query.count())

        # upgrade user
        user = User.query.filter_by(email='hello@world.com').first()
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

        # confirm form
        form = Form.query.first()
        self.client.get('/confirm/%s:%s' % (HASH(form.email, str(form.id)), form.hashid))
        self.assertTrue(Form.query.first().confirmed)
        self.assertEqual(0, Submission.query.count())

        # increase the submission limit
        old_submission_limit = settings.ARCHIVED_SUBMISSIONS_LIMIT
        settings.ARCHIVED_SUBMISSIONS_LIMIT = 10
        # make 5 submissions
        for i in range(5):
            r = self.client.post('/' + form_endpoint,
                headers={'Referer': 'formspree.io'},
                data={'name': 'ana',
                      'submission': '__%s__' % i}
            )

        self.assertEqual(5, Submission.query.count())

        # delete a submission in form
        first_submission = Submission.query.first()
        r = self.client.post('/forms/' + form_endpoint + '/delete/' + unicode(first_submission.id),
            headers={'Referer': settings.SERVICE_URL},
            follow_redirects=True)
        self.assertEqual(200, r.status_code)
        self.assertEqual(4, Submission.query.count())
        self.assertTrue(DB.session.query(Submission.id).filter_by(id='0').scalar() is None) #make sure you deleted the submission

        # logout user
        self.client.get('/logout')

        # attempt to delete form you don't have access to (while logged out)
        r = self.client.post('/forms/' + form_endpoint + '/delete',
            headers={'Referer': settings.SERVICE_URL})
        self.assertEqual(302, r.status_code)
        self.assertEqual(1, Form.query.count())

        # create different user
        r = self.client.post('/register',
            data={'email': 'john@usa.com',
                  'password': 'america'}
        )

        # attempt to delete form we don't have access to
        r = self.client.post('/forms/' + form_endpoint + '/delete',
            headers={'Referer': settings.SERVICE_URL})
        self.assertEqual(400, r.status_code)
        self.assertEqual(1, Form.query.count())

        self.client.get('/logout')

        #log back in to original account
        r = self.client.post('/login',
            data={'email': 'hello@world.com',
                  'password': 'friend'}
        )

        # delete the form created
        r = self.client.post('/forms/' + form_endpoint + '/delete',
            headers={'Referer': settings.SERVICE_URL},
            follow_redirects=True)
        self.assertEqual(200, r.status_code)
        self.assertEqual(0, Form.query.count())

        # reset submission limit
        settings.ARCHIVED_SUBMISSIONS_LIMIT = old_submission_limit

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
        self.assertIn("You've cancelled your subscription and it is ending on", r.data)

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

    def test_user_card_management(self):
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

        # add another card
        token = stripe.Token.create(card={
            'number': '4012888888881881',
            'exp_month': '11',
            'exp_year':'2021',
            'cvc': '345',
        })['id']
        r = self.client.post('/card/add', data={
            'stripeToken': token
        })
        
        customer = stripe.Customer.retrieve(user.stripe_id)
        cards = customer.sources.all(object='card').data
        self.assertEqual(len(cards), 2)
        
        # add a duplicate card
        token = stripe.Token.create(card={
            'number': '4242424242424242',
            'exp_month': '11',
            'exp_year':'2026',
            'cvc': '123',
        })['id']
        r = self.client.post('/card/add', data={
            'stripeToken': token
        }, follow_redirects=True)
        self.assertIn('That card already exists in your wallet', r.data)
        
        # delete a card
        r = self.client.post('/card/%s/delete' % cards[1].id)
        cards = customer.sources.all(object='card').data
        self.assertEqual(len(cards), 1)
        
        # delete the customer
        customer.delete()
