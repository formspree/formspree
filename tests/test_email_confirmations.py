import httpretty
import re
from urllib import unquote

from formspree import settings
from formspree.app import DB
from formspree.users.models import User, Email

from formspree_test_case import FormspreeTestCase

class EmailConfirmationsTestCase(FormspreeTestCase):

    @httpretty.activate
    def test_user_registers_and_adds_emails(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        # register
        r = self.client.post('/register',
            data={'email': 'alice@springs.com',
                  'password': 'canada'}
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.location.endswith('/account/confirm'))
        self.assertEqual(1, User.query.count())

        # add more emails
        user = User.query.filter_by(email='alice@springs.com').first()
        emails = ['alice@example.com', 'team@alice.com', 'extra@email.io']
        for i, addr in enumerate(emails):
            self.client.post('/account/add-email', data={'address': addr})

            txt = unquote(httpretty.last_request().body)
            matchlink = re.search('Link:\+([^?]+)\?(\S+)', txt)
            self.assertTrue(matchlink)

            link = matchlink.group(1)
            qs = matchlink.group(2)
            self.client.get(link, query_string=qs)

            email = Email.query.get([addr, user.id])
            self.assertEqual(Email.query.count(), i+1) # do not count alice@springs.com
            self.assertIsNotNone(email)
            self.assertEqual(email.owner_id, user.id)
