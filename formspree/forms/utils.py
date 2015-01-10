from datetime import timedelta
from functools import update_wrapper
from formspree import settings, log
from flask import make_response, current_app, request, url_for, jsonify, render_template, redirect
import flask
import werkzeug.datastructures
import urlparse
import requests
import uuid
import re
import hashlib

HASH = lambda x, y: hashlib.md5(x+y+settings.NONCE_SECRET).hexdigest()
IS_VALID_EMAIL = lambda x: re.match(r"[^@]+@[^@]+\.[^@]+", x)
EXCLUDE_KEYS = ['_gotcha', '_next', '_subject', '_cc']

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


def get_url(endpoint, secure=False, **values):
    ''' protocol preserving url_for '''
    path = url_for(endpoint, **values)
    if secure:
        url_parts = request.url.split('/', 3)
        path = "https://" + url_parts[2] + path
    return path

def ordered_storage(f):
    '''
    By default Flask doesn't maintain order of form arguments, pretty crazy
    From: https://gist.github.com/cbsmith/5069769
    '''

    def decorator(*args, **kwargs):
        flask.request.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
        return f(*args, **kwargs)
    return decorator

def referrer_to_path(r):
    log.debug('Referrer was %s' % str(r))
    if not r:
        return ''
    parsed = urlparse.urlparse(r)
    return parsed.netloc + parsed.path


def http_form_to_dict(data):
    '''
    Forms are ImmutableMultiDicts,
    convert to json-serializable version
    '''

    ret = {}
    ordered_keys = []

    for elem in data.iteritems(multi=True):
        if not elem[0] in ret.keys():
            ret[elem[0]] = []

            if not elem[0] in EXCLUDE_KEYS:
                ordered_keys.append(elem[0])

        ret[elem[0]].append(elem[1])

    for r in ret.keys():
        ret[r] = ', '.join(ret[r])

    return ret, ordered_keys


def send_email(to=None, subject=None, text=None, html=None, sender=None, cc=None, reply_to=None):
    '''
    Sends email using Mailgun's REST-api
    '''

    if None in [to, subject, text, sender]:
        raise ValueError('to, subject text and sender are required to send email')

    data = {'api_user': settings.SENDGRID_USERNAME,
            'api_key': settings.SENDGRID_PASSWORD,
            'to': to,
            'subject': subject,
            'text': text,
            'html': html}

    # parse 'fromname' from 'sender' if it is formatted like "Name <name@email.com>"
    try:
        bracket = sender.index('<')
        data.update({
            'from': sender[bracket+1:-1],
            'fromname': sender[:bracket].strip()
        })
    except ValueError:
        data.update({'from': sender})

    if reply_to and IS_VALID_EMAIL(reply_to):
        data.update({'replyto': reply_to})

    if cc and IS_VALID_EMAIL(cc):
        data.update({'cc': cc})

    log.info('Queuing message to %s' % str(to))

    result = requests.post(
        'https://api.sendgrid.com/api/mail.send.json',
        data=data
    )

    log.info('Queued message to %s' % str(to))
    errmsg = ""
    if result.status_code / 100 != 2:
        try:
            errmsg = '; \n'.join(result.json().get("errors"))
        except ValueError:
            errmsg = result.text
        log.warning(errmsg)

    return result.status_code / 100 == 2, errmsg
