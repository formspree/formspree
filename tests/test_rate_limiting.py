import httpretty

from formspree import settings
from formspree.app import DB
from formspree.forms.models import Form
from formspree_test_case import FormspreeTestCase


class RateLimitingTestCase(FormspreeTestCase):
    @httpretty.activate
    def test_rate_limiting_on_form_posts(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        # confirm a form
        self.client.post('/alice@example.com',
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
            r = self.client.post('/alice@example.com',
                headers={'referer': 'http://somewhere.com'},
                data={'name': 'attacker'}
            )
            replies.append(r.status_code)

        limit = int(settings.RATE_LIMIT.split(' ')[0])

        # the number of submissions should not be more than the rate limit
        form = Form.query.filter_by(host='somewhere.com', email='alice@example.com').first()
        self.assertLess(form.counter, limit)

        # should have gotten some 302 and then many 429 responses
        self.assertLessEqual(replies.count(302), limit)
        self.assertGreaterEqual(replies.count(429), 900-limit)
