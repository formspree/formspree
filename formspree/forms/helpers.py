from formspree import settings, log
import flask
import werkzeug.datastructures
import urlparse
import requests
import re
import hashlib
import hashids

HASH = lambda x, y: hashlib.md5(x+y+settings.NONCE_SECRET).hexdigest()
EXCLUDE_KEYS = ['_gotcha', '_next', '_subject', '_cc', '_bcc']
MONTHLY_COUNTER_KEY = 'monthly_{form_id}_{month}'.format
HASHIDS_CODEC = hashids.Hashids(alphabet='abcdefghijklmnopqrstuvwxyz',
                                min_length=8,
                                salt=settings.HASHIDS_SALT)

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
