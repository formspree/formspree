import httpretty
import urllib2
import json
import re

from formspree.forms.models import Form
from formspree import settings
from formspree.app import DB

from formspree_test_case import FormspreeTestCase

class ListUnsubscribeTestCase(FormspreeTestCase):
    @httpretty.activate
    def test_list_unsubscribe(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        r = self.client.post('/bob@testwebsite.com',
            headers = {'Referer': 'http://testwebsite.com'},
            data={'name': 'bob'}
        )
        f = Form.query.first()

        # List-Unsubscribe is present on confirmation email
        body = urllib2.unquote(httpretty.last_request().body)
        res = re.search('"List-Unsubscribe":[^"]*"<([^>]+)>"', body)
        self.assertTrue(res is not None)
        list_unsubscribe_url = res.group(1)

        f.confirmed = True
        DB.session.add(f)
        DB.session.commit()

        r = self.client.post('/bob@testwebsite.com',
            headers = {'Referer': 'http://testwebsite.com'},
            data={'name': 'carol'}
        )

        self.assertEqual(r.status_code, 302)

        # List-Unsubscribe is present on normal submission
        body = urllib2.unquote(httpretty.last_request().body)
        res = re.search('"List-Unsubscribe":[^"]*"<([^>]+)>"', body)
        self.assertTrue(res is not None)
        url = res.group(1)
        self.assertEqual(url, list_unsubscribe_url)

        r = self.client.post(url)
        self.assert200(r)

        f = Form.query.first()
        self.assertEqual(f.confirm_sent, True)
        self.assertEqual(f.confirmed, False)
