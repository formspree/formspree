from formspree import settings
from formspree.stuff import DB
from formspree.forms.models import Form

def test_rate_limiting_on_form_posts(client, msend):
    # confirm a form
    client.post('/alice@example.com',
        headers={'referer': 'http://somewhere.com'},
        data={'name': 'john'}
    )
    form = Form.query.filter_by(host='somewhere.com', email='alice@example.com').first()
    form.confirmed = True
    DB.session.add(form)
    DB.session.commit()

    # submit form many times
    replies = []
    for _ in range(1000):
        r = client.post('/alice@example.com',
            headers={'referer': 'http://somewhere.com'},
            data={'name': 'attacker'}
        )
        replies.append(r.status_code)

    limit = int(settings.RATE_LIMIT.split(' ')[0])

    # the number of submissions should not be more than the rate limit
    form = Form.query.filter_by(host='somewhere.com', email='alice@example.com').first()
    assert form.counter < limit

    # should have gotten some 302 and then many 429 responses
    assert replies.count(302) <= limit
    assert replies.count(429) >= 900 - limit
