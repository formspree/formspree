from formspree.utils import next_url
from formspree.users.helpers import send_downgrade_email

def test_next_url(client):
    # thanks route should have the referrer as its 'next'
    assert '/thanks?next=http%3A%2F%2Ffun.io' == next_url(referrer='http://fun.io')

    # No referrer and relative next url should result in proper relative next url.
    assert '/thank-you' == next_url(next='/thank-you')

    # No referrer and absolute next url should result in proper absolute next url.
    assert 'http://somesite.org/thank-you' == next_url(next='http://somesite.org/thank-you')

    # Referrer set and relative next url should result in proper absolute next url.
    assert 'http://fun.io/' == next_url(referrer='http://fun.io', next='/')
    assert 'http://fun.io/thanks.html' == next_url(referrer='http://fun.io', next='thanks.html')
    assert 'http://fun.io/thanks.html' == next_url(referrer='http://fun.io', next='/thanks.html')

    # Referrer set and absolute next url should result in proper absolute next url.
    assert 'https://morefun.net/awesome.php' == next_url(referrer='https://fun.io', next='//morefun.net/awesome.php')
    assert 'http://morefun.net/awesome.php' == next_url(referrer='http://fun.io', next='//morefun.net/awesome.php')

def test_send_downgrade_email(msend):
    send_downgrade_email('whatever@example.com')
    assert msend.called
    assert msend.call_args[1]['to'] == 'whatever@example.com'
    assert 'Successfully downgraded from' in msend.call_args[1]['subject']
