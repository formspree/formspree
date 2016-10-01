# encoding: utf-8

import httpretty
import json

from formspree import settings
from formspree.app import DB
from formspree.users.models import User, Email
from formspree.forms.models import Form

from formspree_test_case import FormspreeTestCase
from utils import parse_confirmation_link_sent

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
        self.assertTrue(r.location.endswith('/account'))
        self.assertEqual(1, User.query.count())

        # add more emails
        user = User.query.filter_by(email='alice@springs.com').first()
        emails = ['alice@example.com', 'team@alice.com', 'extra@email.io']
        for i, addr in enumerate(emails):
            self.client.post('/account/add-email', data={'address': addr})

            link, qs = parse_confirmation_link_sent(httpretty.last_request().body)
            self.client.get(link, query_string=qs)

            email = Email.query.get([addr, user.id])
            self.assertEqual(Email.query.count(), i+1) # do not count alice@springs.com
            self.assertIsNotNone(email)
            self.assertEqual(email.owner_id, user.id)

    @httpretty.activate
    def test_user_gets_previous_forms_assigned_to_him(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        # verify a form for márkö@example.com
        self.client.post(u'/márkö@example.com',
            headers = {'Referer': 'tomatoes.com'},
            data={'name': 'alice'}
        )
        f = Form.query.filter_by(host='tomatoes.com', email=u'márkö@example.com').first()
        f.confirm_sent = True
        f.confirmed = True
        DB.session.add(f)
        DB.session.commit()

        # register márkö@example.com
        r = self.client.post('/register',
            data={'email': u'márkö@example.com',
                  'password': 'russia'}
        )

        # confirm that the user account doesn't have access to the form
        r = self.client.get('/forms',
            headers={'Accept': 'application/json'},
        )
        forms = json.loads(r.data)['forms']
        self.assertEqual(0, len(forms))

        # verify user email
        link, qs = parse_confirmation_link_sent(httpretty.last_request().body)
        self.client.get(link, query_string=qs)

        # confirm that the user has no access to the form since he is not upgraded
        r = self.client.get('/forms',
            headers={'Accept': 'application/json'},
        )
        forms = json.loads(r.data)['forms']
        self.assertEqual(0, len(forms))

        # upgrade user
        user = User.query.filter_by(email=u'márkö@example.com').first()
        user.upgraded = True
        DB.session.add(user)
        DB.session.commit()

        # confirm that the user account has access to the form
        r = self.client.get('/forms',
            headers={'Accept': 'application/json'},
        )
        forms = json.loads(r.data)['forms']
        self.assertEqual(1, len(forms))
        self.assertEqual(forms[0]['email'], u'márkö@example.com')
        self.assertEqual(forms[0]['host'], 'tomatoes.com')

        # verify a form for another address
        r = self.client.post('/contact@mark.com',
            headers = {'Referer': 'mark.com'},
            data={'name': 'luke'}
        )
        f = Form.query.filter_by(host='mark.com', email='contact@mark.com').first()
        f.confirm_sent = True
        f.confirmed = True
        DB.session.add(f)
        DB.session.commit()

        # confirm that the user account doesn't have access to the form
        r = self.client.get('/forms',
            headers={'Accept': 'application/json'},
        )
        forms = json.loads(r.data)['forms']
        self.assertEqual(1, len(forms))

        # add this other email address to user account
        self.client.post('/account/add-email', data={'address': 'contact@mark.com'})

        link, qs = parse_confirmation_link_sent(httpretty.last_request().body)
        self.client.get(link, query_string=qs)

        # confirm that the user account now has access to the form
        r = self.client.get('/forms',
            headers={'Accept': 'application/json'},
        )
        forms = json.loads(r.data)['forms']
        self.assertEqual(2, len(forms))
        self.assertEqual(forms[0]['email'], 'contact@mark.com') # forms are sorted by -id, so the newer comes first
        self.assertEqual(forms[0]['host'], 'mark.com')

        # create a new form spontaneously with an email already verified
        r = self.client.post(u'/márkö@example.com',
            headers = {'Referer': 'elsewhere.com'},
            data={'name': 'luke'}
        )
        f = Form.query.filter_by(host='elsewhere.com', email=u'márkö@example.com').first()
        f.confirm_sent = True
        f.confirmed = True
        DB.session.add(f)
        DB.session.commit()

        # confirm that the user has already accessto that form
        r = self.client.get('/forms',
            headers={'Accept': 'application/json'},
        )
        forms = json.loads(r.data)['forms']
        self.assertEqual(3, len(forms))
        self.assertEqual(forms[0]['email'], u'márkö@example.com')
        self.assertEqual(forms[0]['host'], 'elsewhere.com')
