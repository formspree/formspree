from formspree_test_case import FormspreeTestCase

from formspree.utils import next_url


class UtilsTest(FormspreeTestCase):
    def test_next_url(self):
        # thanks route should have the referrer as its 'next'
        self.assertEqual('/thanks?next=http%3A%2F%2Ffun.io', next_url(referrer='http://fun.io'))

        # No referrer and relative next url should result in proper relative next url.
        self.assertEqual('/thank-you', next_url(next='/thank-you'))

        # No referrer and absolute next url should result in proper absolute next url.
        self.assertEqual('http://somesite.org/thank-you', next_url(next='http://somesite.org/thank-you'))

        # Referrer set and relative next url should result in proper absolute next url.
        self.assertEqual('http://fun.io/', next_url(referrer='http://fun.io', next='/'))
        self.assertEqual('http://fun.io/thanks.html', next_url(referrer='http://fun.io', next='thanks.html'))
        self.assertEqual('http://fun.io/thanks.html', next_url(referrer='http://fun.io', next='/thanks.html'))

        # Referrer set and absolute next url should result in proper absolute next url.
        self.assertEqual('//morefun.net/awesome.php', next_url(referrer='http://fun.io', next='//morefun.net/awesome.php'))
