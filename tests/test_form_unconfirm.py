import httpretty

from formspree.app import DB
from formspree.forms.models import Form

from formspree_test_case import FormspreeTestCase


class FormPostsTestCase(FormspreeTestCase):
    @httpretty.activate
    def test_unconfirm_form(self):
        # manually verify luke@example.com
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
        r = self.client.post('/luke@example.com',
            headers={'Referer': 'http://example.com'},
            data={'name': 'luke'}
        )
        f = Form.query.first()
        f.confirm_sent = True
        f.confirmed = True
        DB.session.add(f)
        DB.session.commit()

        # unconfirm (skips the email/recaptcha/email flow)
        r = self.client.get('/unconfirm/' + f.hash)
        self.assertEqual(r.status_code, 200)
        self.assertIn('Form disabled', r.data)

        # try to submit again (should show confirmation screen)
        r = self.client.post('/luke@example.com',
            headers={'Referer': 'http://example.com'},
            data={'name': 'han'}
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn('Confirm your email', r.data)
