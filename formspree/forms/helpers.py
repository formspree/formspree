from formspree import settings, log
import flask
import werkzeug.datastructures
import urlparse
import requests
import re
import hashlib
import hashids

HASH = lambda x, y: hashlib.md5(x+y+settings.NONCE_SECRET).hexdigest()
IS_VALID_EMAIL = lambda x: re.match(r"[^@]+@[^@]+\.[^@]+", x)
EXCLUDE_KEYS = ['_gotcha', '_next', '_subject', '_cc']
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
