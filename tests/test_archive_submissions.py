import httpretty
import json

from formspree import settings
from formspree.app import DB
from formspree.forms.helpers import HASH
from formspree.users.models import User
from formspree.forms.models import Form, Submission

from formspree_test_case import FormspreeTestCase

class ArchiveSubmissionsTestCase(FormspreeTestCase):
    @httpretty.activate
    def test_automatically_created_forms(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        # submit a form
        self.client.post('/alice@example.com',
            headers = {'referer': 'http://somewhere.com'},
            data={'name': 'john'}
        )
        query = Form.query.filter_by(host='somewhere.com',
                                     email='alice@example.com')
        self.assertEqual(query.count(), 1)
        form = query.first()

        # this form wasn't confirmed, so it still has no submissions
        self.assertEqual(form.submissions.count(), 0)

        # confirm form
        form.confirmed = True
        DB.session.add(form)
        DB.session.commit()

        # submit again
        self.client.post('/alice@example.com',
            headers = {'referer': 'http://somewhere.com'},
            data={'_replyto': 'johann@gmail.com', 'name': 'johann'}
        )

        # submissions now must be 1
        form = query.first()
        self.assertEqual(form.submissions.count(), 1)

        # submit again
        self.client.post('/alice@example.com',
            headers = {'referer': 'http://somewhere.com'},
            data={'_replyto': 'joh@ann.es', '_next': 'http://google.com',
                  'name': 'johannes', 'message': 'salve!'}
        )
        
        # submissions now must be 2
        form = query.first()
        self.assertEqual(form.submissions.count(), 2)

        # check archived values
        submissions = form.submissions.all()

        self.assertEqual(2, len(submissions))
        self.assertNotIn('message', submissions[1].data)
        self.assertNotIn('_next', submissions[1].data)
        self.assertIn('_next', submissions[0].data)
        self.assertEqual('johann@gmail.com', submissions[1].data['_replyto'])
        self.assertEqual('joh@ann.es', submissions[0].data['_replyto'])
        self.assertEqual('johann', submissions[1].data['name'])
        self.assertEqual('johannes', submissions[0].data['name'])
        self.assertEqual('salve!', submissions[0].data['message'])

        # check if submissions over the limit are correctly deleted
        self.assertEqual(settings.ARCHIVED_SUBMISSIONS_LIMIT, 2)

        self.client.post('/alice@example.com',
            headers = {'referer': 'http://somewhere.com'},
            data={'which-submission-is-this': 'the third!'}
        )
        self.assertEqual(2, form.submissions.count())
        newest = form.submissions.first() # first should be the newest
        self.assertEqual(newest.data['which-submission-is-this'], 'the third!')

        self.client.post('/alice@example.com',
            headers = {'referer': 'http://somewhere.com'},
            data={'which-submission-is-this': 'the fourth!'}
        )
        self.assertEqual(2, form.submissions.count())
        newest, last = form.submissions.all()
        self.assertEqual(newest.data['which-submission-is-this'], 'the fourth!')
        self.assertEqual(last.data['which-submission-is-this'], 'the third!')

    @httpretty.activate
    def test_upgraded_user_access(self):
        httpretty.register_uri(httpretty.POST, 'https://api.sendgrid.com/api/mail.send.json')

        # register user
        r = self.client.post('/register',
            data={'email': 'colorado@springs.com',
                  'password': 'banana'}
        )

        # upgrade user manually
        user = User.query.filter_by(email='colorado@springs.com').first()
        user.upgraded = True
        DB.session.add(user)
        DB.session.commit()

        # create form
        r = self.client.post('/forms',
            headers={'Accept': 'application/json',
                     'Content-type': 'application/json'},
            data=json.dumps({'email': 'hope@springs.com'})
        )
        resp = json.loads(r.data)
        form_endpoint = resp['random_like_string']

        # manually confirm the form
        form = Form.get_form_by_random_like_string(form_endpoint)
        form.confirmed = True
        DB.session.add(form)
        DB.session.commit()
        
        # submit form
        r = self.client.post('/' + form_endpoint,
            headers={'Referer': 'formspree.io'},
            data={'name': 'bruce', 'message': 'hi!'}
        )

        # test submissions endpoint (/forms/<random_like_string>/)
        r = self.client.get('/forms/' + form_endpoint + '/',
                            headers={'Accept': 'application/json'})
        submissions = json.loads(r.data)['submissions']

        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0]['name'], 'bruce')
        self.assertEqual(submissions[0]['message'], 'hi!')

        # test submissions endpoint with the user downgraded
        user.upgraded = False
        DB.session.add(user)
        DB.session.commit()
        r = self.client.get('/forms/' + form_endpoint + '/')
        self.assertEqual(r.status_code, 402) # it should fail

        # test submissions endpoint without a logged user
        self.client.get('/logout')
        r = self.client.get('/forms/' + form_endpoint + '/')
        self.assertEqual(r.status_code, 302) # it should return a redirect (via @user_required)
