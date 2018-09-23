import json

from formspree import settings
from formspree.stuff import DB
from formspree.forms.helpers import HASH
from formspree.users.models import User, Email, Plan
from formspree.forms.models import Form, Submission

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
        headers={'Referer': 'http://testsite.com'},
        data={'name': 'bruce'}
    )
    assert 'sent an email confirmation' in r.data.decode('utf-8')
    assert 'confirm your email' in msend.call_args[1]['text']
    assert 1 == Form.query.count()

    # confirm form
    form = Form.query.first()
    client.get('/confirm/%s:%s' % (HASH(form.email, str(form.id)), form.hashid))
    assert Form.query.first().confirmed

    # Make sure that it marks the first form as AJAX
    assert Form.query.first().uses_ajax

    # send 5 forms (monthly limits should not apply to the gold user)
    assert settings.MONTHLY_SUBMISSIONS_LIMIT == 2
    for i in range(5):
        r = client.post(
            "/" + form_endpoint,
            headers={"Referer": "testsite.com"},
            data={"name": "ana", "submission": "__%s__" % i},
        )
    form = Form.query.first()
    assert form.counter == 5
    assert form.get_monthly_counter() == 5
    assert 'ana' in msend.call_args[1]['text']
    assert '__4__' in msend.call_args[1]['text']
    assert 'past the limit' not in msend.call_args[1]['text']

    # try (and fail) to submit from a different host
    r = client.post(
        "/" + form_endpoint, headers={"Referer": "bad.com"}, data={"name": "usurper"}
    )
    assert r.status_code == 403
    assert "ana" in msend.call_args[1]["text"]  # no more data is sent to sendgrid
    assert "__4__" in msend.call_args[1]["text"]


def test_form_creation_with_a_registered_email(client, msend):
    # register user
    r = client.post(
        "/register", data={"email": "user@testsite.com", "password": "banana"}
    )
    # upgrade user manually
    user = User.query.filter_by(email="user@testsite.com").first()
    user.plan = Plan.gold
    DB.session.add(user)
    DB.session.commit()

    # creating a form without providing an url should not send verification email
    msend.reset_mock()
    r = client.post(
        "/api-int/forms",
        headers={
            "Accept": "application/json",
            "Content-type": "application/json",
            "Referer": settings.SERVICE_URL,
        },
        data=json.dumps({"email": "email@testsite.com"}),
    )
    assert not msend.called

    # create form without a confirmed email should send a verification email
    msend.reset_mock()
    r = client.post(
        "/api-int/forms",
        headers={
            "Accept": "application/json",
            "Content-type": "application/json",
            "Referer": settings.SERVICE_URL,
        },
        data=json.dumps(
            {
                "email": "email@testsite.com",
                "url": "https://www.testsite.com/contact.html",
            }
        ),
    )
    resp = json.loads(r.data.decode("utf-8"))
    assert resp["confirmed"] == False
    assert msend.called
    assert "Confirm email for" in msend.call_args[1]["subject"]
    assert "www.testsite.com/contact.html" in msend.call_args[1]["text"]

    # manually verify an email
    email = Email()
    email.address = "owned-by@testsite.com"
    email.owner_id = user.id
    DB.session.add(email)
    DB.session.commit()

    # create a form with the verified email address
    r = client.post(
        "/api-int/forms",
        headers={
            "Accept": "application/json",
            "Content-type": "application/json",
            "Referer": settings.SERVICE_URL,
        },
        data=json.dumps(
            {
                "email": "owned-by@testsite.com",
                "url": "https://www.testsite.com/about.html",
            }
        ),
    )
    resp = json.loads(r.data.decode("utf-8"))
    assert resp["confirmed"] == True
    assert (
        "www.testsite.com/contact.html" in msend.call_args[1]["text"]
    )  # same as the last, means no new request was made

    # should have three created forms in the end
    assert Form.query.count() == 3


def test_sitewide_forms(client, msend, mocker):
    m_sitewidecheck = mocker.patch(
        "formspree.forms.api.sitewide_file_check", side_effect=[True, True, True]
    )

    # register user
    r = client.post(
        "/register", data={"email": "user@testsite.com", "password": "banana"}
    )
    # upgrade user manually
    user = User.query.filter_by(email="user@testsite.com").first()
    user.plan = Plan.gold
    DB.session.add(user)
    DB.session.commit()

    # manually verify an email
    email = Email()
    email.address = "myüñìćõð€email@email.com"
    email.owner_id = user.id
    DB.session.add(email)
    DB.session.commit()

    # create a sitewide form with the verified email address
    r = client.post(
        "/api-int/forms",
        headers={
            "Accept": "application/json",
            "Content-type": "application/json",
            "Referer": settings.SERVICE_URL,
        },
        data=json.dumps(
            {
                "email": "myüñìćõð€email@email.com",
                "url": "http://mysite.com",
                "sitewide": "true",
            }
        ),
    )
    resp = json.loads(r.data.decode("utf-8"))

    assert m_sitewidecheck.called
    assert m_sitewidecheck.call_args[0][1] == "myüñìćõð€email@email.com"
    assert resp["confirmed"]
    m_sitewidecheck.reset_mock()

    assert 1 == Form.query.count()
    forms = Form.query.all()
    form = forms[0]
    assert form.sitewide
    assert form.host == "mysite.com"

    # submit form
    r = client.post(
        "/" + form.hashid,
        headers={
            "Referer": "http://www.mysite.com/hipopotamo",
            "content-type": "application/json",
        },
        data=json.dumps({"name": "alice"}),
    )
    assert "alice" in msend.call_args[1]["text"]

    client.post(
        "/" + form.hashid,
        headers={
            "Referer": "http://mysite.com/baleia/urso?w=2",
            "content-type": "application/json",
        },
        data=json.dumps({"name": "maria"}),
    )
    assert "maria" in msend.call_args[1]["text"]

    client.post(
        "/" + form.hashid,
        headers={"Referer": "http://mysite.com/", "content-type": "application/json"},
        data=json.dumps({"name": "laura"}),
    )
    assert "laura" in msend.call_args[1]["text"]

    # another form, now with a www prefix that will be stripped
    r = client.post(
        "/api-int/forms",
        headers={
            "Accept": "application/json",
            "Content-type": "application/json",
            "Referer": settings.SERVICE_URL,
        },
        data=json.dumps(
            {
                "email": "myüñìćõð€email@email.com",
                "url": "http://www.naive.com",
                "sitewide": "true",
            }
        ),
    )
    resp = json.loads(r.data.decode("utf-8"))

    assert m_sitewidecheck.called
    assert m_sitewidecheck.call_args[0][0] == "http://www.naive.com"
    assert resp["confirmed"]

    assert 2 == Form.query.count()
    forms = Form.query.all()
    form = forms[1]
    assert form.sitewide
    assert form.host == "naive.com"

    # submit form
    r = client.post(
        "/" + form.hashid,
        headers={
            "Referer": "http://naive.com/hipopotamo",
            "content-type": "application/json",
        },
        data=json.dumps({"name": "alice"}),
    )
    assert "alice" in msend.call_args[1]["text"]

    client.post(
        "/" + form.hashid,
        headers={
            "Referer": "http://www.naive.com/baleia/urso?w=2",
            "content-type": "application/json",
        },
        data=json.dumps({"name": "maria"}),
    )
    assert "maria" in msend.call_args[1]["text"]

    client.post(
        "/" + form.hashid,
        headers={
            "Referer": "http://www.naive.com/",
            "content-type": "application/json",
        },
        data=json.dumps({"name": "laura"}),
    )
    assert "laura" in msend.call_args[1]["text"]

    # create a different form with the same email address, now using unprefixed url
    r = client.post(
        "/api-int/forms",
        headers={
            "Accept": "application/json",
            "Content-type": "application/json",
            "Referer": settings.SERVICE_URL,
        },
        data=json.dumps(
            {
                "email": "myüñìćõð€email@email.com",
                "url": "mysite.com",
                "sitewide": "true",
            }
        ),
    )
    resp = json.loads(r.data.decode("utf-8"))


def test_form_settings(client, msend):
    # register and upgrade user
    client.post("/register", data={"email": "texas@springs.com", "password": "water"})
    user = User.query.filter_by(email="texas@springs.com").first()
    user.plan = Plan.gold
    DB.session.add(user)
    DB.session.commit()

    # create and confirm form
    r = client.post(
        "/api-int/forms",
        headers={
            "Accept": "application/json",
            "Content-type": "application/json",
            "Referer": settings.SERVICE_URL,
        },
        data=json.dumps({"email": "texas@springs.com"}),
    )
    resp = json.loads(r.data.decode("utf-8"))
    form = Form.query.first()
    form.confirmed = True
    DB.session.add(form)
    DB.session.commit()
    form_endpoint = resp["hashid"]

    # disable email notifications on this form
    msend.reset_mock()

    client.patch(
        "/api-int/forms/" + form_endpoint,
        headers={"Referer": settings.SERVICE_URL},
        content_type="application/json",
        data=json.dumps({"disable_email": True}),
    )
    assert Form.query.first().disable_email

    # post to form
    client.post(
        "/" + form_endpoint,
        headers={"Referer": "http://testsite.com"},
        data={"name": "bruce"},
    )
    # make sure it doesn't send the email
    assert not msend.called

    # disable archive storage on this form
    client.patch(
        "/api-int/forms/" + form_endpoint,
        headers={"Referer": settings.SERVICE_URL},
        content_type="application/json",
        data=json.dumps({"disable_storage": True}),
    )
    assert Form.query.first().disable_storage

    # make sure that we know there's one submission in database from first submission
    assert 1 == Submission.query.count()

    # make sure that the submission wasn't stored in the database
    # post to form
    client.post(
        "/" + form_endpoint,
        headers={"Referer": "http://testsite.com"},
        data={"name": "wayne"},
    )
    assert 1 == Submission.query.count()

    # enable email notifications on this form
    client.patch(
        "/api-int/forms/" + form_endpoint,
        headers={"Referer": settings.SERVICE_URL},
        content_type="application/json",
        data=json.dumps({"disable_email": False}),
    )
    assert not Form.query.first().disable_email

    # make sure that our form still isn't storing submissions
    assert 1 == Submission.query.count()

    # enable archive storage again
    client.patch(
        "/api-int/forms/" + form_endpoint,
        headers={"Referer": settings.SERVICE_URL},
        content_type="application/json",
        data=json.dumps({"disable_storage": False}),
    )
    assert not Form.query.first().disable_storage

    # post to form again this time it should store the submission
    client.post(
        "/" + form_endpoint,
        headers={"Referer": "http://testsite.com"},
        data={"name": "luke"},
    )
    assert 2 == Submission.query.filter_by(form_id=form.id).count()

    # check captcha disabling
    assert not Form.query.first().captcha_disabled

    client.patch(
        "/api-int/forms/" + form_endpoint,
        headers={"Referer": settings.SERVICE_URL},
        content_type="application/json",
        data=json.dumps({"captcha_disabled": True}),
    )
    assert Form.query.first().captcha_disabled

    client.patch(
        "/api-int/forms/" + form_endpoint,
        headers={"Referer": settings.SERVICE_URL},
        content_type="application/json",
        data=json.dumps({"captcha_disabled": False}),
    )
    assert not Form.query.first().captcha_disabled
