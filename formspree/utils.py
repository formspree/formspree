import datetime
import calendar
from datetime import timedelta
from functools import update_wrapper
from flask import make_response, current_app, request, url_for, jsonify
from importlib import import_module

import string
import uuid

# decorators

def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers
            h['Access-Control-Allow-Origin'] = origin

            if request.method == 'OPTIONS':
                h['Access-Control-Allow-Methods'] = get_methods()
                h['Access-Control-Max-Age'] = str(max_age)
                if headers is not None:
                    h['Access-Control-Allow-Headers'] = headers

            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator


def request_wants_json():
    if request.headers.get('X_REQUESTED_WITH','').lower() == 'xmlhttprequest':
        return True
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']


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


def int2bigstring(n):
    n += 1000
    n = n * n
    return ''.join(string.ascii_lowercase[int(i)] for i in str(n))


def bigstring2int(s):
    n = int(''.join(str(string.ascii_lowercase.index(l)) for l in s))
    n = n**0.5
    return int(n - 1000)


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
