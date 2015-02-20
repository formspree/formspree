import httpretty
import json

from formspree.forms.models import Form
from formspree.app import DB

from formspree_test_case import FormspreeTestCase

class ContentTypeTestCase(FormspreeTestCase):

    @httpretty.activate
    def test_various_content_types(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')
        r = self.client.post('/bob@example.com',
            headers = {'Referer': 'http://example.com'},
            data={'name': 'bob'}
        )
        f = Form.query.first()
        f.confirm_sent = True
        f.confirmed = True
        DB.session.add(f)
        DB.session.commit()

        def isjson(res):
            try:
                json.loads(res.get_data())
                assert(res.mimetype == 'application/json')
                return True
            except ValueError:
                return False

        def ishtml(res):
            try:
                json.loads(res.get_data())
                return False
            except ValueError:
                assert(res.mimetype == 'text/html')
                return True

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

        for ct, acc, check in types:
            headers = {'Referer': 'http://example.com'}
            if ct:
                headers['Content-Type'] = ct
            if acc:
                headers['Accept'] = acc

            data = {'name': 'bob'}
            data = json.dumps(data) if ct and 'json' in ct else data

            # print 'SENT'
            # print 'headers', headers
            # print type(data), data
            # print '\n'

            res = self.client.post('/bob@example.com',
                headers=headers,
                data=data
            )

            # print 'GOT'
            # print res.headers
            # print res.get_data()
            # print '\n'

            assertion = check(res)
            self.assertTrue(assertion)










