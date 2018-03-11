import requests
import datetime
import calendar
import urlparse
import uuid
import json
import re
from flask import request, url_for, jsonify, g

from formspree import settings

IS_VALID_EMAIL = lambda x: re.match(r"[^@]+@[^@]+\.[^@]+", x)

def valid_url(url):
    parsed = urlparse.urlparse(url)
    return len(parsed.scheme) > 0 and len(parsed.netloc) > 0 and not 'javascript:' in url

def request_wants_json():
    if request.headers.get('X_REQUESTED_WITH', '').lower() == 'xmlhttprequest' or \
       request.headers.get('X-REQUESTED-WITH', '').lower() == 'xmlhttprequest':
        return True
    if accept_better('json', 'html'):
        return True
    if 'json' in request.headers.get('Content-Type', '') and \
            not accept_better('html', 'json'):
        return True
    return False


def accept_better(subject, against):
    if 'Accept' in request.headers:
        accept = request.headers['Accept'].lower()
        try:
            isub = accept.index(subject)
        except ValueError:
            return False

        try:
            iaga = accept.index(against)
        except ValueError:
            return True

        return isub < iaga
    else:
        return False


def jsonerror(code, *args, **kwargs):
    resp = jsonify(*args, **kwargs)
    resp.status_code = code
    return resp


def uuidslug():
    return uuid2slug(uuid.uuid4())


def uuid2slug(uuidobj):
    return uuidobj.bytes.encode('base64').rstrip('=\n').replace('/', '_')


def slug2uuid(slug):
    return str(
        uuid.UUID(bytes=(slug + '==').replace('_', '/').decode('base64'))
    )


def get_url(endpoint, secure=False, **values):
    ''' protocol preserving url_for '''
    path = url_for(endpoint, **values)
    if secure:
        url_parts = request.url.split('/', 3)
        path = "https://" + url_parts[2] + path
    return path


def url_domain(url):
    parsed = urlparse.urlparse(url)
    return '.'.join(parsed.netloc.split('.')[-2:])


def unix_time_for_12_months_from_now(now=None):
    now = now or datetime.date.today()
    month = now.month - 1 + 12
    next_year = now.year + month / 12
    next_month = month % 12 + 1
    start_of_next_month = datetime.datetime(next_year, next_month, 1, 0, 0)
    return calendar.timegm(start_of_next_month.utctimetuple())


def unix_time_for_5_min_from_now(now=None):
    now = now or datetime.datetime.now()
    five_min_later = now + datetime.timedelta(minutes=5)
    return calendar.timegm(five_min_later.utctimetuple())


def next_url(referrer=None, next=None):
    referrer = referrer if referrer is not None else ''

    if next:
        # use the referrer as base, replace its parts with the provided
        # parts from _next. so, if _next is only a path it will just use
        # that path. if it is a netloc without a scheme, will use that
        # netloc, but reuse the scheme from base and so on.
        parsed_next = urlparse.urlparse(next)
        base = urlparse.urlparse(referrer)

        return urlparse.urlunparse([
            parsed_next.scheme or base.scheme,
            parsed_next.netloc or base.netloc,
            parsed_next.path or base.path,
            parsed_next.params or base.params,
            parsed_next.query or base.query,
            parsed_next.fragment or base.fragment,
        ])
    else:
        return url_for('thanks', next=referrer)


def send_email(to=None, subject=None, text=None, html=None,
               sender=None, cc=None, reply_to=None, headers=None):
    g.log = g.log.new(to=to, sender=sender)

    if None in [to, subject, text, sender]:
        raise ValueError('to, subject text and sender required to send email')

    data = {'api_user': settings.SENDGRID_USERNAME,
            'api_key': settings.SENDGRID_PASSWORD,
            'to': to,
            'subject': subject,
            'text': text,
            'html': html}

    # parse 'fromname' from 'sender' if it is
    # formatted like "Name <name@email.com>"
    try:
        bracket = sender.index('<')
        data.update({
            'from': sender[bracket+1:-1],
            'fromname': sender[:bracket].strip()
        })
    except ValueError:
        data.update({'from': sender})

    if headers:
        data.update({'headers': json.dumps(headers)})

    if reply_to:
        data.update({'replyto': reply_to})

    if cc:
        valid_emails = [email for email in cc if IS_VALID_EMAIL(email)]
        data.update({'cc': valid_emails})

    result = requests.post(
        'https://api.sendgrid.com/api/mail.send.json',
        data=data
    )

    errmsg = ""
    if result.status_code / 100 != 2:
        try:
            errmsg = '; \n'.join(result.json().get("errors"))
        except ValueError:
            errmsg = result.text
        g.log.warning('Could not send email.', err=errmsg)
    else:
        g.log.info('Sent email.', to=to)

    return result.status_code / 100 == 2, errmsg, result.status_code
