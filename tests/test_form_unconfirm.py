import httpretty

from formspree.app import DB
from formspree.forms.models import Form
from formspree.forms.helpers import temp_store_forms_to_disable

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

        # request unconfirm (bypassing the email + select forms + captcha process)
        nonce = temp_store_forms_to_disable([f.id])

        # proceed to unconfirm
        r = self.client.get('/unconfirm/' + nonce)
        self.assertEqual(r.status_code, 200)
        self.assertIn('Forms disabled', r.data)

        # try to submit again (should show confirmation screen)
        httpretty.reset()
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
        r = self.client.post('/luke@example.com',
            headers={'Referer': 'http://example.com'},
            data={'name': 'han'}
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn('Confirm your email', r.data)
        self.assertFalse(httpretty.has_request())
