import datetime
import calendar
from datetime import timedelta
import urlparse
from flask import make_response, current_app, request, url_for, jsonify
from importlib import import_module

import string
import uuid

# decorators

def request_wants_json():
    if request.headers.get('X_REQUESTED_WITH','').lower() == 'xmlhttprequest':
        return True
    if accept_better('json', 'html'):
        return True
    if 'json' in request.headers.get('Content-Type', '') and \
            not accept_better('html', 'json'):
        return True


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
    return str(uuid.UUID(bytes=(slug + '==').replace('_', '/').decode('base64')))


def get_url(endpoint, secure=False, **values):   
    ''' protocol preserving url_for '''
    path = url_for(endpoint, **values)
    if secure:
        url_parts = request.url.split('/', 3)
        path = "https://" + url_parts[2] + path
    return path


def unix_time_for_12_months_from_now(now=None):
    now = now or datetime.date.today()
    month = now.month - 1 + 12
    next_year = now.year + month / 12
    next_month = month % 12 + 1
    start_of_next_month = datetime.datetime(next_year, next_month, 1, 0, 0)
    return calendar.timegm(start_of_next_month.utctimetuple())


def next_url(referrer=None, next=None):
    referrer = referrer if referrer is not None else ''
    next = next if next is not None else ''

    if not next:
      return url_for('thanks')

    if urlparse.urlparse(next).netloc:  # check if next_url is an absolute url
      return next

    parsed = list(urlparse.urlparse(referrer))  # results in [scheme, netloc, path, ...]
    parsed[2] = next

    return urlparse.urlunparse(parsed)
