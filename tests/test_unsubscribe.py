from urllib.parse import unquote
from flask import url_for

from formspree.forms.models import Form
from formspree import settings
from formspree.stuff import DB

def test_unconfirm_process(client, msend):
    # confirm some forms for the same email address
    f1 = Form('bob@testwebsite.com', 'testwebsite.com')
    f1.confirmed = True
    DB.session.add(f1)

    f2 = Form('bob@testwebsite.com', 'othertestwebsite.com')
    f2.confirmed = True
    DB.session.add(f2)

    f3 = Form('bob@testwebsite.com', 'anothertestwebsite.com')
    f3.confirmed = True
    DB.session.add(f3)
    DB.session.commit()

    # try a submission
    r = client.post('/bob@testwebsite.com',
        headers = {'Referer': 'http://testwebsite.com'},
        data={'name': 'carol'}
    )
    assert msend.called
    request_unconfirm_url = url_for('request_unconfirm_form', form_id=f1.id, _external=True)
    assert request_unconfirm_url in msend.call_args[1]['text']
    msend.reset_mock()

    # this should send a confirmation email
    r = client.get(request_unconfirm_url)

    # actually, it should fail unless the request comes from a browser
    assert not msend.called

    # now it must work
    r = client.get(request_unconfirm_url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:62.0) Gecko/20100101 Firefox/62.0'})
    assert r.status_code == 200
    assert msend.called

    unconfirm_url_with_digest = url_for(
        'unconfirm_form',
        form_id=f1.id,
        digest=f1.unconfirm_digest(),
        _external=True
    )
    assert unconfirm_url_with_digest in msend.call_args[1]['text']
    msend.reset_mock()
    
    # unconfirm this
    r = client.get(unconfirm_url_with_digest)
    assert f1.confirmed == False

    # should show a page with the other options
    assert r.status_code == 200
    assert 'Select all' in r.data.decode('utf-8')
    assert f2.host in r.data.decode('utf-8')
    assert f3.host in r.data.decode('utf-8')

    unconfirm_multiple_url = url_for('unconfirm_multiple')
    assert unconfirm_multiple_url in r.data.decode('utf-8')

    # we can use unconfirm_multiple to unconfirm f2
    assert f2.confirmed == True
    r = client.post(unconfirm_multiple_url, data={'form_ids': [f2.id]})
    assert r.status_code == 200
    assert 'Success' in r.data.decode('utf-8')
    assert f2.confirmed == False


def test_list_unsubscribe_post(client, msend):
    r = client.post('/bob@testwebsite.com',
        headers = {'Referer': 'http://testwebsite.com'},
        data={'name': 'bob'}
    )
    f = Form.query.first()

    # List-Unsubscribe header is sent (it is surrounded by brackets <>)
    list_unsubscribe_url = msend.call_args[1]['headers']['List-Unsubscribe'][1:-1]

    f.confirmed = True
    DB.session.add(f)
    DB.session.commit()

    r = client.post('/bob@testwebsite.com',
        headers = {'Referer': 'http://testwebsite.com'},
        data={'name': 'carol'}
    )

    assert r.status_code == 302

    # List-Unsubscribe is present on normal submission
    assert msend.call_args[1]['headers']['List-Unsubscribe'][1:-1] == list_unsubscribe_url

    r = client.post(list_unsubscribe_url)
    assert r.status_code == 200

    f = Form.query.first()
    assert f.confirm_sent == True
    assert f.confirmed == False
