import httpretty

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
        for _ in range(1000):
            self.client.post('/alice@example.com',
                headers={'referer': 'http://somewhere.com'},
                data={'name': 'attacker'}
            )

        # the number of submissions should not be more than the rate limit
        form = Form.query.filter_by(host='somewhere.com', email='alice@example.com').first()
        self.assertLess(form.counter, 30)
