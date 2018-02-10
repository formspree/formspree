import httpretty
import json

from formspree.forms.models import Form
from formspree import settings
from formspree.app import DB

from formspree_test_case import FormspreeTestCase

class ContentTypeTestCase(FormspreeTestCase):

    @httpretty.activate
    def test_various_content_types(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
        r = self.client.post('/bob@testwebsite.com',
            headers = {'Referer': 'http://testwebsite.com'},
            data={'name': 'bob'}
        )
        f = Form.query.first()
        f.confirm_sent = True
        f.confirmed = True
        DB.session.add(f)
        DB.session.commit()

        def isjson(res):
            try:
                d = json.loads(res.get_data())
                self.assertIsInstance(d, dict)
                self.assertIn('success', d)
                self.assertEqual(res.mimetype, 'application/json')
            except ValueError, e:
                self.assertFalse(e)

        def ishtml(res):
            try:
                d = json.loads(res.get_data())
                self.assertNotIsInstance(d, dict)
            except ValueError:
                self.assertEqual(res.mimetype, 'text/html')
                self.assertEqual(res.status_code, 302)

        types = [
             # content-type      # accept     # check
            (None, None, ishtml),
            ('application/json', 'text/json', isjson),
            ('application/json', 'application/json', isjson),
            (None, 'application/json', isjson),
            (None, 'application/json, text/javascript, */*; q=0.01', isjson),
            ('application/json', None, isjson),
            ('application/json', 'application/json, text/plain, */*', isjson),
            ('application/x-www-form-urlencoded', 'application/json', isjson),
            ('application/x-www-form-urlencoded', 'application/json, text/plain, */*', isjson),
            ('application/x-www-form-urlencoded', None, ishtml),
            (None, 'text/html', ishtml),
            ('application/json', 'text/html', ishtml),
            ('application/json', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', ishtml),
            ('application/x-www-form-urlencoded', 'text/html, */*; q=0.01', ishtml),
            (None, 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', ishtml)
        ]

        # for this test only we will relax this limit.
        default_limit = settings.MONTHLY_SUBMISSIONS_LIMIT
        settings.MONTHLY_SUBMISSIONS_LIMIT = len(types)

        for ct, acc, check in types:
            headers = {'Referer': 'http://testwebsite.com'}
            if ct:
                headers['Content-Type'] = ct
            if acc:
                headers['Accept'] = acc

            data = {'name': 'bob'}
            data = json.dumps(data) if ct and 'json' in ct else data

            res = self.client.post('/bob@testwebsite.com',
                headers=headers,
                data=data
            )
            check(res)

            # test all combinations again, but with X-Requested-With header
            # and expect json in all of them
            headers['X-Requested-With'] = 'XMLHttpRequest'

            res = self.client.post('/bob@testwebsite.com',
                headers=headers,
                data=data
            )
            isjson(res)

        # then we put the default limit back
        settings.MONTHLY_SUBMISSIONS_LIMIT = default_limit
