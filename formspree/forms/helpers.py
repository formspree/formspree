import werkzeug.datastructures
import urlparse
import requests
import hashlib
import hashids
import uuid
import json
from urlparse import urljoin
from flask import request, g

from formspree import settings
from formspree.app import redis_store, DB

CAPTCHA_URL = 'https://www.google.com/recaptcha/api/siteverify'
CAPTCHA_VAL = 'g-recaptcha-response'

HASH = lambda x, y: hashlib.md5(x.encode('utf-8')+y.encode('utf-8')+settings.NONCE_SECRET).hexdigest()

KEYS_NOT_STORED = {'_gotcha', '_format', '_language', CAPTCHA_VAL, '_host_nonce'}
KEYS_EXCLUDED_FROM_EMAIL = KEYS_NOT_STORED.union({'_subject', '_cc', '_next'})

REDIS_COUNTER_KEY = 'monthly_{form_id}_{month}'.format
REDIS_HOSTNAME_KEY = 'hostname_{nonce}'.format
REDIS_FIRSTSUBMISSION_KEY = 'first_{nonce}'.format
HASHIDS_CODEC = hashids.Hashids(alphabet='abcdefghijklmnopqrstuvwxyz',
                                min_length=8,
                                salt=settings.HASHIDS_SALT)


def ordered_storage(f):
    '''
    By default Flask doesn't maintain order of form arguments, pretty crazy
    From: https://gist.github.com/cbsmith/5069769
    '''

    def decorator(*args, **kwargs):
        request.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
        return f(*args, **kwargs)
    return decorator


def referrer_to_path(r):
    if not r:
        return ''
    parsed = urlparse.urlparse(r)
    n = parsed.netloc + parsed.path
    return n


def referrer_to_baseurl(r):
    if not r:
        return ''
    parsed = urlparse.urlparse(r)
    n = parsed.netloc
    return n


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
            ordered_keys.append(elem[0])

        ret[elem[0]].append(elem[1])

    for k, v in ret.items():
        ret[k] = ', '.join(v)

    return ret, ordered_keys


def remove_www(host):
    if host.startswith('www.'):
        return host[4:]
    return host


def sitewide_file_check(url, email):
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'http://' + url
    url = urljoin(url, '/formspree-verify.txt')

    g.log = g.log.bind(url=url, email=email)

    res = requests.get(url, timeout=3, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/55.0.2883.87 Chrome/55.0.2883.87 Safari/537.36'
    })
    if not res.ok:
        g.log.debug('Sitewide file not found.', contents=res.text[:100])
        return False

    for line in res.text.splitlines():
        line = line.strip(u'\xef\xbb\xbf ')
        if line == email:
            g.log.debug('Email found in sitewide file.')
            return True

    g.log.warn('Email not found in sitewide file.', contents=res.text[:100])
    return False


def verify_captcha(form_data, request):
    if not CAPTCHA_VAL in form_data:
        return False
    r = requests.post(CAPTCHA_URL, data={
        'secret': settings.RECAPTCHA_SECRET,
        'response': form_data[CAPTCHA_VAL],
        'remoteip': request.remote_addr,
    }, timeout=2)
    return r.ok and r.json().get('success')


def valid_domain_request(request):
    # check that this request came from user dashboard to prevent XSS and CSRF
    referrer = referrer_to_baseurl(request.referrer)
    service = referrer_to_baseurl(settings.SERVICE_URL)

    return referrer == service


def assign_ajax(form, sent_using_ajax):
    if form.uses_ajax is None:
        form.uses_ajax = sent_using_ajax
        DB.session.add(form)
        DB.session.commit()


def temp_store_hostname(hostname, referrer):
    nonce = uuid.uuid4()
    key = REDIS_HOSTNAME_KEY(nonce=nonce)
    redis_store.set(key, hostname+','+referrer)
    redis_store.expire(key, 300000)
    return nonce


def get_temp_hostname(nonce):
    key = REDIS_HOSTNAME_KEY(nonce=nonce)
    value = redis_store.get(key)
    if value is None:
        raise KeyError("no temp_hostname stored.")
    redis_store.delete(key)
    values = value.split(',')
    if len(values) != 2:
        raise ValueError("temp_hostname value is invalid: " + value)
    else:
        return values


def store_first_submission(nonce, data):
    key = REDIS_FIRSTSUBMISSION_KEY(nonce=nonce)
    redis_store.set(key, json.dumps(data))
    redis_store.expire(key, 300000)


def fetch_first_submission(nonce):
    key = REDIS_FIRSTSUBMISSION_KEY(nonce=nonce)
    jsondata = redis_store.get(key)
    try:
        return json.loads(jsondata)
    except:
        return None
