import json
import time
import stripe

from formspree import settings
from formspree.stuff import DB
from formspree.forms.helpers import HASH
from formspree.users.models import User, Email, Plan
from formspree.forms.models import Form, Submission

from .conftest import parse_confirmation_link_sent

def test_register_page(client, msend):
    r = client.get('/register')
    assert 200 == r.status_code

def test_login_page(client, msend):
    r = client.get('/login')
    assert 200 == r.status_code

def test_forgot_password_page(client, msend):
    r = client.get('/login/reset')
    assert 200 == r.status_code

def test_user_auth(client, msend):
    # register
    r = client.post('/register',
        data={'email': 'alice@springs.com',
              'password': 'canada'}
    )
    assert r.status_code == 302
    assert r.location.endswith('/account')
    assert 1 == User.query.count()

    # email confirmation
    user = User.query.filter_by(email='alice@springs.com').first()
    assert Email.query.get(['alice@springs.com', user.id]) is None

    assert msend.called
    link, qs = parse_confirmation_link_sent(msend.call_args[1]['text'])
    client.get(
        link,
        query_string=qs,
        follow_redirects=True
    )
    email = Email.query.get(['alice@springs.com', user.id])
    assert Email.query.count() == 1
    assert email is not None
    assert email.owner_id == user.id

    # logout
    r = client.get('/logout')
    assert r.status_code == 302
    assert 1 == User.query.count()

    # login   
    r = client.post('/login',
        data={'email': 'alice@springs.com',
              'password': 'canada'}
    )
    assert r.status_code == 302
    assert r.location.endswith('/dashboard')
    assert 1 == User.query.count()

def test_forgot_password(client, msend):
    # register
    r = client.post('/register',
        data={'email': 'fragile@yes.com',
              'password': 'roundabout'}
    )
    assert 1 == User.query.count()
    initial_password = User.query.all()[0].password

    # logout
    client.get('/logout')

    # forget password
    r = client.post('/login/reset',
        data={'email': 'fragile@yes.com'}
    )
    assert r.status_code == 200

    # click on the email link
    link, qs = parse_confirmation_link_sent( msend.call_args[1]['text'])
    r = client.get(
        link,
        query_string=qs,
        follow_redirects=True
    )
    assert r.status_code == 200

    # send new passwords (not matching)
    r = client.post(link, data={'password1': 'verdes', 'password2': 'roxas'})
    assert r.status_code == 302
    assert r.location == link
    assert User.query.all()[0].password == initial_password

    # again, now matching
    r = client.post(link, data={'password1': 'amarelas', 'password2': 'amarelas'})
    assert r.status_code == 302
    assert r.location.endswith('/dashboard')
    assert User.query.all()[0].password != initial_password
    

def test_form_creation(client, msend):
    # register user
    r = client.post('/register',
        data={'email': 'colorado@springs.com',
              'password': 'banana'}
    )
    assert r.status_code == 302
    assert 1 == User.query.count()

    # fail to create form
    r = client.post(
        "/api-int/forms",
        headers={"Content-type": "application/json", "Referer": settings.SERVICE_URL},
        data={"email": "hope@springs.com"},
    )
    assert r.status_code == 402
    assert 'error' in json.loads(r.data.decode('utf-8'))
    assert 0 == Form.query.count()

    # upgrade user manually
    user = User.query.filter_by(email='colorado@springs.com').first()
    user.plan = Plan.gold
    DB.session.add(user)
    DB.session.commit()

    # successfully create form
    r = client.post(
        "/api-int/forms",
        headers={"Content-type": "application/json", "Referer": settings.SERVICE_URL},
        data=json.dumps({"email": "hope@springs.com"}),
    )
    resp = json.loads(r.data.decode('utf-8'))
    assert r.status_code == 200
    assert 'submission_url' in resp
    assert 'hashid' in resp
    form_endpoint = resp['hashid']
    assert resp['hashid'] in resp['submission_url']
    assert 1 == Form.query.count()
    assert Form.query.first().id == Form.get_with_hashid(resp['hashid']).id

    # post to form
    r = client.post('/' + form_endpoint,
        headers={'Referer': 'formspree.io'},
        data={'name': 'bruce'}
    )
    assert "We've sent a link to your email" in r.data.decode('utf-8')
    assert 'confirm your email' in msend.call_args[1]['text']
    assert 1 == Form.query.count()

    # confirm form
    form = Form.query.first()
    client.get('/confirm/%s:%s' % (HASH(form.email, str(form.id)), form.hashid))
    assert Form.query.first().confirmed

    # send 5 forms (monthly limits should not apply to the gold user)
    assert settings.MONTHLY_SUBMISSIONS_LIMIT == 2
    for i in range(5):
        r = client.post('/' + form_endpoint,
            headers={'Referer': 'formspree.io'},
            data={'name': 'ana',
                  'submission': '__%s__' % i}
        )
    form = Form.query.first()
    assert form.counter == 5
    assert form.get_monthly_counter() == 5
    assert 'ana' in msend.call_args[1]['text']
    assert '__4__' in msend.call_args[1]['text']
    assert 'past the limit' not in msend.call_args[1]['text']

    # try (and fail) to submit from a different host
    r = client.post('/' + form_endpoint,
        headers={'Referer': 'bad.com'},
        data={'name': 'usurper'}
    )
    assert r.status_code == 403
    # no more data is sent to sendgrid
    assert 'ana' in msend.call_args[1]['text']
    assert '__4__' in msend.call_args[1]['text']

def test_form_toggle(client, msend):
    # create and login a user
    r = client.post('/register',
        data={'email': 'hello@world.com',
              'password': 'friend'}
    )
    assert r.status_code == 302
    assert 1 == User.query.count()

    # upgrade user
    user = User.query.filter_by(email='hello@world.com').first()
    user.plan = Plan.gold
    DB.session.add(user)
    DB.session.commit()

    # successfully create form
    r = client.post(
        "/api-int/forms",
        headers={"Referer": settings.SERVICE_URL, "Content-type": "application/json"},
        data=json.dumps({"email": "hope@springs.com"}),
    )
    resp = json.loads(r.data.decode('utf-8'))
    assert r.status_code == 200
    assert 'submission_url' in resp
    assert 'hashid' in resp
    form_endpoint = resp['hashid']
    assert resp['hashid'] in resp['submission_url']
    assert 1 == Form.query.count()
    assert Form.query.first().id == Form.get_with_hashid(resp['hashid']).id

    # post to form
    r = client.post('/' + form_endpoint,
        headers={'Referer': 'formspree.io'},
        data={'name': 'bruce'}
    )

    # confirm form
    form = Form.query.first()
    client.get('/confirm/%s:%s' % (HASH(form.email, str(form.id)), form.hashid))
    assert Form.query.first().confirmed
    assert 0 == Submission.query.count()

    # disable the form
    r = client.patch(
        "/api-int/forms/" + form_endpoint,
        headers={"Referer": settings.SERVICE_URL, "Content-Type": "application/json"},
        data=json.dumps({"disabled": True}),
    )
    assert 200 == r.status_code
    assert r.json["ok"]
    assert Form.query.first().disabled
    assert 0 == Form.query.first().counter

    # logout and attempt to enable the form
    client.get("/logout")
    r = client.patch(
        "/api-int/forms/" + form_endpoint,
        headers={"Content-Type": "application/json", "Referer": settings.SERVICE_URL},
        data=json.dumps({"disabled": True}),
    )
    assert 401 == r.status_code
    assert "error" in json.loads(r.data.decode("utf-8"))
    assert Form.query.first().disabled

    # fail when attempting to post to form
    r = client.post('/' + form_endpoint,
        headers={'Referer': 'formspree.io'},
        data={'name': 'bruce'}
    )
    assert 403 == r.status_code
    assert 0 == Form.query.first().counter

    # log back in and re-enable form
    r = client.post("/login", data={"email": "hello@world.com", "password": "friend"})
    r = client.patch(
        "/api-int/forms/" + form_endpoint,
        headers={"Referer": settings.SERVICE_URL, "Content-Type": "application/json"},
        data=json.dumps({"disabled": False}),
    )
    assert 200 == r.status_code
    assert not Form.query.first().disabled

    # successfully post to form
    r = client.post('/' + form_endpoint,
        headers={'Referer': 'formspree.io'},
        data={'name': 'bruce'}
    )
    assert 1 == Form.query.first().counter

def test_form_and_submission_deletion(client, msend):
    # create and login a user
    r = client.post('/register',
        data={'email': 'hello@world.com',
              'password': 'friend'}
    )
    assert r.status_code == 302
    assert 1 == User.query.count()

    # upgrade user
    user = User.query.filter_by(email='hello@world.com').first()
    user.plan = Plan.gold
    DB.session.add(user)
    DB.session.commit()

    # successfully create form
    r = client.post(
        "/api-int/forms",
        headers={
            "Accept": "application/json",
            "Content-type": "application/json",
            "Referer": settings.SERVICE_URL,
        },
        data=json.dumps({"email": "hope@springs.com"}),
    )
    resp = json.loads(r.data.decode('utf-8'))
    assert r.status_code == 200
    assert 'submission_url' in resp
    assert 'hashid' in resp
    form_endpoint = resp['hashid']
    assert resp['hashid'] in resp['submission_url']
    assert 1 == Form.query.count()
    assert Form.query.first().id == Form.get_with_hashid(resp['hashid']).id

    # post to form
    r = client.post('/' + form_endpoint,
        headers={'Referer': 'formspree.io'},
        data={'name': 'bruce'}
    )

    # confirm form
    form = Form.query.first()
    client.get('/confirm/%s:%s' % (HASH(form.email, str(form.id)), form.hashid))
    assert Form.query.first().confirmed
    assert 0 == Submission.query.count()

    # increase the submission limit
    old_submission_limit = settings.ARCHIVED_SUBMISSIONS_LIMIT
    settings.ARCHIVED_SUBMISSIONS_LIMIT = 10
    # make 5 submissions
    for i in range(5):
        r = client.post('/' + form_endpoint,
            headers={'Referer': 'formspree.io'},
            data={'name': 'ana',
                  'submission': '__%s__' % i}
        )

    assert 5 == Submission.query.count()

    # delete a submission in form
    first_submission = Submission.query.first()
    r = client.delete(
        "/api-int/forms/" + form_endpoint + "/submissions/" + str(first_submission.id),
        headers={"Referer": settings.SERVICE_URL},
    )
    assert 200 == r.status_code
    assert 4 == Submission.query.count()
    assert DB.session.query(Submission.id).filter_by(id='0').scalar() is None
    # make sure you've deleted the submission

    # logout user
    client.get('/logout')

    # attempt to delete form you don't have access to (while logged out)
    r = client.delete(
        "/api-int/forms/" + form_endpoint, headers={"Referer": settings.SERVICE_URL}
    )
    assert 401 == r.status_code
    assert 1 == Form.query.count()

    # create different user
    r = client.post('/register',
        data={'email': 'john@usa.com',
              'password': 'america'}
    )

    # attempt to delete form we don't have access to
    r = client.delete(
        "/api-int/forms/" + form_endpoint, headers={"Referer": settings.SERVICE_URL}
    )
    assert 401 == r.status_code
    assert 1 == Form.query.count()

    client.get('/logout')

    #log back in to original account
    r = client.post('/login',
        data={'email': 'hello@world.com',
              'password': 'friend'}
    )

    # delete the form created
    r = client.delete(
        "/api-int/forms/" + form_endpoint, headers={"Referer": settings.SERVICE_URL}
    )
    assert 200 == r.status_code
    assert 0 == Form.query.count()

    # reset submission limit
    settings.ARCHIVED_SUBMISSIONS_LIMIT = old_submission_limit

def test_user_upgrade_and_downgrade(client, msend, mocker):
    # check correct usage of stripe test keys during test
    assert '_test_' in settings.STRIPE_PUBLISHABLE_KEY
    assert '_test_' in settings.STRIPE_SECRET_KEY
    assert stripe.api_key in settings.STRIPE_TEST_SECRET_KEY

    # register user
    r = client.post('/register',
        data={'email': 'maria@example.com',
              'password': 'uva'}
    )
    assert r.status_code == 302
    assert msend.called
    assert msend.call_args[1]['to'] == 'maria@example.com'
    assert 'Confirm email for your account' in msend.call_args[1]['subject']
    msend.reset_mock()

    user = User.query.filter_by(email='maria@example.com').first()
    assert user.plan == Plan.free
    
    # subscribe with card through stripe
    token = stripe.Token.create(card={
        'number': '4242424242424242',
        'exp_month': '11',
        'exp_year':'2026',
        'cvc': '123',
    })['id']

    r = client.post('/account/upgrade', data={
        'stripeToken': token
    })

    user = User.query.filter_by(email='maria@example.com').first()
    assert user.plan == Plan.gold

    # downgrade back to the free plan
    r = client.post('/account/downgrade', follow_redirects=True)

    # redirect back to /account, the HTML shows that the user is not yet
    # in the free plan, since it will be valid for the next 30 days
    assert "You've cancelled your subscription and it is ending on" in r.data.decode('utf-8')

    user = User.query.filter_by(email='maria@example.com').first()
    assert user.plan == Plan.gold

    customer = stripe.Customer.retrieve(user.stripe_id)
    assert customer.subscriptions.data[0].cancel_at_period_end == True

    # simulate stripe webhook reporting that the plan has been canceled just now
    m_senddowngraded = mocker.patch('formspree.users.views.send_downgrade_email.delay')
    customer.subscriptions.data[0].delete()
    # this will send webhooks automatically only for 
    # endpoints registered on the stripe dashboard

    client.post('/webhooks/stripe', data=json.dumps({
        'type': 'customer.subscription.deleted',
        'data': {
            'object': {
                'customer': user.stripe_id
            }
        }
    }), headers={'Content-type': 'application/json'})

    user = User.query.filter_by(email='maria@example.com').first()
    assert user.plan == Plan.free
    assert m_senddowngraded.called

    # delete the stripe customer
    customer.delete()

def test_user_card_management(client, msend):
    # check correct usage of stripe test keys during test
    assert '_test_' in settings.STRIPE_PUBLISHABLE_KEY
    assert '_test_' in settings.STRIPE_SECRET_KEY
    assert stripe.api_key in settings.STRIPE_TEST_SECRET_KEY

    # register user
    r = client.post('/register',
        data={'email': 'maria@example.com',
              'password': 'uva'}
    )
    assert r.status_code == 302

    user = User.query.filter_by(email='maria@example.com').first()
    assert user.plan == Plan.free
    
    # subscribe with card through stripe
    token = stripe.Token.create(card={
        'number': '4242424242424242',
        'exp_month': '11',
        'exp_year':'2026',
        'cvc': '123',
    })['id']
    r = client.post('/account/upgrade', data={
        'stripeToken': token
    })

    user = User.query.filter_by(email='maria@example.com').first()
    assert user.plan == Plan.gold

    # add another card
    token = stripe.Token.create(card={
        'number': '4012888888881881',
        'exp_month': '11',
        'exp_year':'2021',
        'cvc': '345',
    })['id']
    r = client.post('/card/add', data={
        'stripeToken': token
    })
    
    customer = stripe.Customer.retrieve(user.stripe_id)
    cards = customer.sources.all(object='card').data
    assert len(cards) == 2
    
    # add a duplicate card
    token = stripe.Token.create(card={
        'number': '4242424242424242',
        'exp_month': '11',
        'exp_year':'2026',
        'cvc': '123',
    })['id']
    r = client.post('/card/add', data={
        'stripeToken': token
    }, follow_redirects=True)
    assert 'That card already exists in your wallet' in r.data.decode('utf-8')
    
    # delete a card
    r = client.post('/card/%s/delete' % cards[1].id)
    cards = customer.sources.all(object='card').data
    assert len(cards) == 1
    
    # delete the customer
    customer.delete()
