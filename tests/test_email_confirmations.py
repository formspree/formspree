import json

from formspree import settings
from formspree.stuff import DB
from formspree.users.models import User, Email, Plan
from formspree.forms.models import Form

from .conftest import parse_confirmation_link_sent

def test_user_registers_and_adds_emails(client, msend):
    # register
    r = client.post('/register',
        data={'email': 'alice@springs.com',
              'password': 'canada'}
    )
    assert r.status_code == 302
    assert r.location.endswith('/account')
    assert 1 == User.query.count()

    # add more emails
    user = User.query.filter_by(email='alice@springs.com').first()
    emails = ['alice@example.com', 'team@alice.com', 'extra@email.io']
    for i, addr in enumerate(emails):
        client.post('/account/add-email', data={'address': addr})

        link, qs = parse_confirmation_link_sent(msend.call_args[1]['text'])
        client.get(link, query_string=qs)

        email = Email.query.get([addr, user.id])
        assert Email.query.count() == i+1 # do not count alice@springs.com
        assert email is not None
        assert email.owner_id == user.id

def test_user_gets_previous_forms_assigned_to_him(client, msend):
    # verify a form for márkö@example.com
    client.post(u'/márkö@example.com',
        headers = {'Referer': 'tomatoes.com'},
        data={'name': 'alice'}
    )
    f = Form.query.filter_by(host='tomatoes.com', email=u'márkö@example.com').first()
    f.confirm_sent = True
    f.confirmed = True
    DB.session.add(f)
    DB.session.commit()

    # register márkö@example.com
    r = client.post('/register',
        data={'email': u'márkö@example.com',
              'password': 'russia'}
    )

    # confirm that the user account doesn't have access to the form
    r = client.get(
        "/api-int/forms",
        headers={"Accept": "application/json", "Referer": settings.SERVICE_URL},
    )
    forms = json.loads(r.data.decode('utf-8'))['forms']
    assert 0 == len(forms)

    # verify user email
    link, qs = parse_confirmation_link_sent(msend.call_args[1]['text'])
    client.get(link, query_string=qs)

    # confirm that the user has no access to the form since he is not gold
    r = client.get(
        "/api-int/forms",
        headers={"Accept": "application/json", "Referer": settings.SERVICE_URL},
    )
    forms = json.loads(r.data.decode('utf-8'))['forms']
    assert 0 == len(forms)

    # upgrade user
    user = User.query.filter_by(email=u'márkö@example.com').first()
    user.plan = Plan.gold
    DB.session.add(user)
    DB.session.commit()

    # confirm that the user account has access to the form
    r = client.get(
        "/api-int/forms",
        headers={"Accept": "application/json", "Referer": settings.SERVICE_URL},
    )
    forms = json.loads(r.data.decode('utf-8'))['forms']
    assert 1 == len(forms)
    assert forms[0]['email'] == u'márkö@example.com'
    assert forms[0]['host'] == 'tomatoes.com'

    # verify a form for another address
    r = client.post('/contact@mark.com',
        headers = {'Referer': 'mark.com'},
        data={'name': 'luke'}
    )
    f = Form.query.filter_by(host='mark.com', email='contact@mark.com').first()
    f.confirm_sent = True
    f.confirmed = True
    DB.session.add(f)
    DB.session.commit()

    # confirm that the user account doesn't have access to the form
    r = client.get(
        "/api-int/forms",
        headers={"Accept": "application/json", "Referer": settings.SERVICE_URL},
    )
    forms = json.loads(r.data.decode('utf-8'))['forms']
    assert 1 == len(forms)

    # add this other email address to user account
    client.post('/account/add-email', data={'address': 'contact@mark.com'})

    link, qs = parse_confirmation_link_sent(msend.call_args[1]['text'])
    client.get(link, query_string=qs)

    # confirm that the user account now has access to the form
    r = client.get(
        "/api-int/forms",
        headers={"Accept": "application/json", "Referer": settings.SERVICE_URL},
    )
    forms = json.loads(r.data.decode('utf-8'))['forms']
    assert 2 == len(forms)
    assert forms[0]['email'] == 'contact@mark.com' # forms are sorted by -id, so the newer comes first
    assert forms[0]['host'] == 'mark.com'

    # create a new form spontaneously with an email already verified
    r = client.post(u'/márkö@example.com',
        headers = {'Referer': 'elsewhere.com'},
        data={'name': 'luke'}
    )
    f = Form.query.filter_by(host='elsewhere.com', email=u'márkö@example.com').first()
    f.confirm_sent = True
    f.confirmed = True
    DB.session.add(f)
    DB.session.commit()

    # confirm that the user has already accessto that form
    r = client.get(
        "/api-int/forms",
        headers={"Accept": "application/json", "Referer": settings.SERVICE_URL},
    )
    forms = json.loads(r.data.decode('utf-8'))['forms']
    assert 3 == len(forms)
    assert forms[0]['email'] == u'márkö@example.com'
    assert forms[0]['host'] == 'elsewhere.com'
