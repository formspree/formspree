from urllib.parse import unquote

from formspree.forms.models import Form
from formspree import settings
from formspree.stuff import DB

def test_list_unsubscribe(client, msend):
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
