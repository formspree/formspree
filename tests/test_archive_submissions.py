import json

from formspree import settings
from formspree.stuff import DB
from formspree.forms.helpers import HASH
from formspree.users.models import User, Plan
from formspree.forms.models import Form, Submission

def test_automatically_created_forms(client, msend):
    # submit a form
    client.post('/alice@example.com',
        headers = {'referer': 'http://somewhere.com'},
        data={'name': 'john'}
    )
    query = Form.query.filter_by(host='somewhere.com',
                                 email='alice@example.com')
    assert query.count() == 1
    form = query.first()

    # this form wasn't confirmed, so it still has no submissions
    assert form.submissions.count() == 0

    # confirm form
    form.confirmed = True
    DB.session.add(form)
    DB.session.commit()

    # submit again
    client.post('/alice@example.com',
        headers = {'referer': 'http://somewhere.com'},
        data={'_replyto': 'johann@gmail.com', 'name': 'johann'}
    )

    # submissions now must be 1
    form = query.first()
    assert form.submissions.count() == 1

    # submit again
    client.post('/alice@example.com',
        headers = {'referer': 'http://somewhere.com'},
        data={'_replyto': 'joh@ann.es', '_next': 'http://google.com',
              'name': 'johannes', 'message': 'salve!'}
    )
    
    # submissions now must be 2
    form = query.first()
    assert form.submissions.count() == 2

    # check archived values
    submissions = form.submissions.all()

    assert 2 == len(submissions)
    assert 'message' not in submissions[1].data
    assert '_next' not in submissions[1].data
    assert '_next' in submissions[0].data
    assert 'johann@gmail.com' == submissions[1].data['_replyto']
    assert 'joh@ann.es' == submissions[0].data['_replyto']
    assert 'johann' == submissions[1].data['name']
    assert 'johannes' == submissions[0].data['name']
    assert 'salve!' == submissions[0].data['message']

    # check if submissions over the limit are correctly deleted
    assert settings.ARCHIVED_SUBMISSIONS_LIMIT == 2

    client.post('/alice@example.com',
        headers = {'referer': 'http://somewhere.com'},
        data={'which-submission-is-this': 'the third!'}
    )
    assert 2 == form.submissions.count()
    newest = form.submissions.first() # first should be the newest
    assert newest.data['which-submission-is-this'] == 'the third!'

    client.post('/alice@example.com',
        headers = {'referer': 'http://somewhere.com'},
        data={'which-submission-is-this': 'the fourth!'}
    )
    assert 2 == form.submissions.count()
    newest, last = form.submissions.all()
    assert newest.data['which-submission-is-this'] == 'the fourth!'
    assert last.data['which-submission-is-this'] == 'the third!'

    #
    # try another form (to ensure that a form is not deleting wrong submissions)
    client.post('/sokratis@example.com',
        headers = {'referer': 'http://here.com'},
        data={'name': 'send me the confirmation!'}
    )
    query = Form.query.filter_by(host='here.com',
                                 email='sokratis@example.com')
    assert query.count() == 1
    secondform = query.first()

    # this form wasn't confirmed, so it still has no submissions
    assert secondform.submissions.count() == 0

    # confirm
    secondform.confirmed = True
    DB.session.add(form)
    DB.session.commit()

    # submit more times and test
    client.post('/sokratis@example.com',
        headers = {'referer': 'http://here.com'},
        data={'name': 'leibniz'}
    )

    assert 1 == secondform.submissions.count()
    assert secondform.submissions.first().data['name'] == 'leibniz'

    client.post('/sokratis@example.com',
        headers = {'referer': 'http://here.com'},
        data={'name': 'schelling'}
    )

    assert 2 == secondform.submissions.count()
    newest, last = secondform.submissions.all()
    assert newest.data['name'] == 'schelling'
    assert last.data['name'] == 'leibniz'

    client.post('/sokratis@example.com',
        headers = {'referer': 'http://here.com'},
        data={'name': 'husserl'}
    )

    assert 2 == secondform.submissions.count()
    newest, last = secondform.submissions.all()
    assert newest.data['name'] == 'husserl'
    assert last.data['name'] == 'schelling'

    # now check the previous form again
    newest, last = form.submissions.all()
    assert newest.data['which-submission-is-this'] == 'the fourth!'
    assert last.data['which-submission-is-this'] == 'the third!'

    client.post('/alice@example.com',
        headers = {'referer': 'http://somewhere.com'},
        data={'which-submission-is-this': 'the fifth!'}
    )
    assert 2 == form.submissions.count()
    newest, last = form.submissions.all()
    assert newest.data['which-submission-is-this'] == 'the fifth!'
    assert last.data['which-submission-is-this'] == 'the fourth!'

    # just one more time the second form
    assert 2 == secondform.submissions.count()
    newest, last = secondform.submissions.all()
    assert newest.data['name'] == 'husserl'
    assert last.data['name'] == 'schelling'

def test_gold_user_access(client, msend):
    # register user
    r = client.post('/register',
        data={'email': 'colorado@springs.com',
              'password': 'banana'}
    )

    # upgrade user manually
    user = User.query.filter_by(email='colorado@springs.com').first()
    user.plan = Plan.gold
    DB.session.add(user)
    DB.session.commit()

    # create form
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
    form_endpoint = resp['hashid']

    # manually confirm the form
    form = Form.get_with_hashid(form_endpoint)
    form.confirmed = True
    DB.session.add(form)
    DB.session.commit()
    
    # submit form
    r = client.post('/' + form_endpoint,
        headers={'Referer': 'formspree.io'},
        data={'name': 'bruce', 'message': 'hi, my name is bruce!'}
    )

    # test submissions endpoint (/forms/<hashid>/)
    r = client.get(
        "/api-int/forms/" + form_endpoint,
        headers={"Accept": "application/json", "Referer": settings.SERVICE_URL},
    )
    submissions = json.loads(r.data.decode('utf-8'))['submissions']
    assert len(submissions) == 1
    assert submissions[0]['name'] == 'bruce'
    assert submissions[0]['message'] == 'hi, my name is bruce!'

    # test exporting feature (both json and csv file downloads)
    r = client.get('/forms/' + form_endpoint + '.json')
    submissions = json.loads(r.data.decode('utf-8'))['submissions']
    assert len(submissions) == 1
    assert submissions[0]['name'] == 'bruce'
    assert submissions[0]['message'] == 'hi, my name is bruce!'

    r = client.get('/forms/' + form_endpoint + '.csv')
    lines = r.data.decode('utf-8').splitlines()
    assert len(lines) == 2
    assert lines[0] == "id,date,message,name"
    assert '"hi in my name is bruce!"', lines[1]

    # test submissions endpoint with the user downgraded
    user.plan = Plan.free
    DB.session.add(user)
    DB.session.commit()
    r = client.get("/api-int/forms/" + form_endpoint)
    assert r.status_code == 402  # it should fail

    # test submissions endpoint without a logged user
    client.get("/logout")
    r = client.get("/api-int/forms/" + form_endpoint)
    assert r.status_code == 401  # should return a json error (via flask login)
    assert "error" in r.json

def test_grandfather_limit_and_decrease(client, msend):
    settings.GRANDFATHER_MONTHLY_LIMIT = 2
    settings.MONTHLY_SUBMISSIONS_LIMIT = 1
    settings.FORM_LIMIT_DECREASE_ACTIVATION_SEQUENCE = 1
    # the form limit should be 2 for the first form and 1 for the second

    # submit the forms
    client.post('/grandfathered@example.com',
        headers = {'referer': 'http://somewhere.com'},
        data={'name': 'john'}
    )
    form_grandfathered = Form.query.filter_by(host='somewhere.com',
                                 email='grandfathered@example.com').first()

    client.post('/new@example.com',
        headers = {'referer': 'http://somewhere.com'},
        data={'name': 'john'}
    )
    form_new = Form.query.filter_by(host='somewhere.com',
                                 email='new@example.com').first()

    # confirm formS
    form_grandfathered.confirmed = True
    DB.session.add(form_grandfathered)
    form_new.confirmed = True
    DB.session.add(form_new)
    DB.session.commit()

    # submit each form 3 times
    msend.reset_mock()
    for i in range(3):
        client.post('/grandfathered@example.com',
            headers = {'referer': 'http://somewhere.com'},
            data={'_replyto': 'johann@gmail.com', 'name': 'johann', 'value': 'v%s' % i}
        )

    assert len(msend.call_args_list) == 4
    assert 'grandfathered@example.com' == msend.call_args_list[-4][1]['to']
    assert '90%' in msend.call_args_list[-4][1]['text']
    assert 'grandfathered@example.com' == msend.call_args_list[-3][1]['to']
    assert 'v0' in msend.call_args_list[-3][1]['text']
    assert 'grandfathered@example.com' == msend.call_args_list[-2][1]['to']
    assert 'v1' in msend.call_args_list[-2][1]['text']
    assert 'grandfathered@example.com' == msend.call_args_list[-1][1]['to']
    assert 'limit' in msend.call_args_list[-1][1]['text']

    msend.reset_mock()
    for i in range(3):
        client.post('/new@example.com',
            headers = {'referer': 'http://somewhere.com'},
            data={'_replyto': 'johann@gmail.com', 'name': 'johann', 'value': 'v%s' % i}
        )

    assert len(msend.call_args_list) == 3
    assert 'new@example.com' == msend.call_args_list[-3][1]['to']
    assert 'v0' in msend.call_args_list[-3][1]['text']
    assert 'new@example.com' == msend.call_args_list[-2][1]['to']
    assert 'limit' in msend.call_args_list[-2][1]['text']
    assert 'new@example.com' == msend.call_args_list[-1][1]['to']
    assert 'limit' in msend.call_args_list[-1][1]['text']
