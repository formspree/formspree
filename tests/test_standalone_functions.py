from formspree.utils import next_url

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
