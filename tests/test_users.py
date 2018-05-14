import json
import time
import stripe

from formspree import settings
from formspree.users.models import User

def test_user_upgrade_and_downgrade(client, msend, worker):
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
    assert user.upgraded == False
    
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
    assert user.upgraded == True

    # downgrade back to the free plan
    r = client.post('/account/downgrade', follow_redirects=True)

    # redirect back to /account, the HTML shows that the user is not yet
    # in the free plan, since it will be valid for the next 30 days
    assert "You've cancelled your subscription and it is ending on" in r.data.decode('utf-8')

    user = User.query.filter_by(email='maria@example.com').first()
    assert user.upgraded == True

    customer = stripe.Customer.retrieve(user.stripe_id)
    assert customer.subscriptions.data[0].cancel_at_period_end == True

    # simulate stripe webhook reporting that the plan has been canceled just now
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
    assert user.upgraded == False

    worker.idle.wait(10)
    assert msend.called
    assert msend.call_args[1]['to'] == 'maria@example.com'
    assert 'Successfully downgraded' in msend.call_args[1]['subject']

    # delete the stripe customer
    customer.delete()
