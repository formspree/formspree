import requests
import urlparse
import hashlib
import redis
import re

import flask
from flask import request, url_for, render_template, redirect, jsonify

import werkzeug.datastructures

from paste.util.multidict import MultiDict

from utils import crossdomain, request_wants_json, jsonerror
import settings
import log


'''
constants

'''

REDIS = redis.Redis.from_url(settings.REDIS_URL)

DEFAULT_SENDER = settings.DEFAULT_SENDER

HASH = lambda x, y: hashlib.md5(x+y+settings.NONCE_SECRET).hexdigest()
COUNTER_KEY = lambda x, y: 'forms_counter_%s' % HASH(x, y)

NONCE_KEY = lambda x, y: 'forms_nonce_%s' % HASH(x, y)
VALID_NONCE = lambda x: REDIS.get('forms_nonce_%s' % x)

EMAIL_CONFIRMED_KEY = lambda x: 'forms_email_%s' % x
EMAIL_CONFIRMED = lambda x: REDIS.get('forms_email_%s' % x)

HASH_EMAIL_KEY = lambda x: 'forms_hash_email_%s' % x
HASH_EMAIL = lambda x: REDIS.get('forms_hash_email_%s' % x)
HASH_HOST_KEY = lambda x: 'forms_hash_host_%s' % x
HASH_HOST = lambda x: REDIS.get('forms_hash_host_%s' % x)

IS_VALID_EMAIL = lambda x: re.match(r"[^@]+@[^@]+\.[^@]+", x)

EXCLUDE_KEYS = ['_gotcha', '_next', '_subject', '_cc']

''' 
helpers

'''


def ordered_storage(f):
    '''
    By default Flask doesn't maintain order of form arguments, pretty crazy
    From: https://gist.github.com/cbsmith/5069769
    '''

    def decorator(*args, **kwargs):
        flask.request.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
        return f(*args, **kwargs)
    return decorator


def _send_email(to=None, subject=None, text=None, html=None, sender=None, cc=None, reply_to=None):
    '''
    Sends email using Mailgun's REST-api
    '''

    if None in [to, subject, text, sender]:
        raise ValueError('to, subject text and sender are required to send email')

    data = {'from': sender,
            'to': to,
            'subject': subject,
            'text': text,
            'html': html}

    if reply_to and IS_VALID_EMAIL(reply_to):
        data.update({'h:Reply-To': reply_to})

    if cc and IS_VALID_EMAIL(cc):
        data.update({'cc': cc})

    log.info('Queuing message to %s' % str(to))

    result = requests.post(
        'https://api.mailgun.net/v2/%s/messages' % setting.MAILGUN_DOMAIN,
        auth=('api', settings.MAILGUN_API_KEY),
        data=data
    )

    log.info('Queued message to %s' % str(to))
    errmsg = ""
    if result.status_code / 100 != 2:
        try:
            errmsg = result.json().get("message")
        except ValueError:
            errmsg = result.text
        log.warning(errmsg)

    return result.status_code / 100 == 2, errmsg


def _get_values_for_hash(h):
    '''
    We store email and host cleartext for each hash, returns those
    '''

    return HASH_EMAIL(h), HASH_HOST(h)


def _referrer_to_path(r):
    log.debug('Referrer was %s' % str(r))
    if not r:
        return ''
    parsed = urlparse.urlparse(r)
    return parsed.netloc + parsed.path


def _form_to_dict(data):
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


def _send_form(email, host):
    '''
    Sends request.form to user's email. 
    Assumes email has been verified.
    '''

    data, keys = _form_to_dict(request.form)

    subject = data.get('_subject', 'New submission from %s' % _referrer_to_path(request.referrer))
    reply_to = data.get('_replyto', None)
    cc = data.get('_cc', None)
    next = data.get('_next', url_for('thanks', next=request.referrer))
    spam = data.get('_gotcha', None)

    # prevent submitting empty form
    if not any(data.values()):
        if request_wants_json():
            return k(400, {'error': "Can't send an empty form"})
        else:
            return render_template('error.html', 
                                   title='Can\'t send an empty form', 
                                   text=str('<a href="%s">Return to form</a>' % request.referrer)), 400

    if not spam:
        text = render_template('email/form.txt', data=data, host=host, keys=keys)
        html = render_template('email/form.html', data=data, host=host, keys=keys)
        result = _send_email(to=email, 
                          subject=subject,
                          text=text,
                          html=html,
                          sender=DEFAULT_SENDER,
                          reply_to=reply_to,
                          cc=cc)

        if not result[0]:
            if request_wants_json():
                return jsonerror(500, {'error': "Unable to send email"})
            else:
                return render_template('error.html', 
                                       title='Unable to send email', 
                                       text=result[1]), 500

        REDIS.incr(COUNTER_KEY(email, host))

    if request_wants_json():
        return jsonify({'success': "Email sent"})
    else:
        return redirect(next, code=302)


def _send_confirmation(email, host):
    '''
    Helper that actually creates confirmation nonce
    and sends the email to associated email. Renders
    different templates depending on the result
    '''
    log.debug('Sending confirmation')
    if VALID_NONCE(HASH(email, host)):
        log.debug('Confirmation already sent')
        if request_wants_json():
            return jsonify({'success': "confirmation email sent"})
        else:
            return render_template('confirmation_sent.html', email=email, host=host)

    link = url_for('confirm_email', nonce=HASH(email, host), _external=True)
    
    def render_content(type):
        return render_template('email/confirm.%s' % type, 
                                  email=email, 
                                  host=host, 
                                  nonce_link=link)

    log.debug('Sending email')

    result = _send_email(to=email, 
                         subject='Confirm email for %s' % settings.SERVICE_NAME, 
                         text=render_content('txt'),
                         html=render_content('html'), 
                         sender=DEFAULT_SENDER) 

    log.debug('Sent')

    if not result[0]:
        if request_wants_json():
            return jsonerror(500, {'error': "Unable to send email"})
        else:
            return render_template('error.html', 
                                   title='Unable to send email', 
                                   text=result[1]), 500


    REDIS.set(NONCE_KEY(email, host), None)
    REDIS.set(HASH_EMAIL_KEY(HASH(email, host)), email)
    REDIS.set(HASH_HOST_KEY(HASH(email, host)), host)

    if request_wants_json():
        return jsonify({'success': "confirmation email sent"})
    else:
        return render_template('confirmation_sent.html', email=email, host=host)


def nl2br(value): 
    return value.replace('\n','<br>\n')


'''
views

'''


def thanks():
    return render_template('thanks.html')


@crossdomain(origin='*')
@ordered_storage
def send(email):
    ''' 
    Main endpoint, checks if email+host is valid and sends 
    either form data or verification to email 
    '''

    if request.method == 'GET':
        if request_wants_json():
            return jsonerror(405, {'error': "Please submit POST request."})
        else:
            return render_template('info.html', 
                                   title='Form should POST', 
                                   text='Make sure your form has the <span class="code"><strong>method="POST"</strong></span> attribute'), 405

    if not IS_VALID_EMAIL(email):
        if request_wants_json():
            return jsonerror(400, {'error': "Invalid email address"})
        else:
            return render_template('error.html', 
                                   title='Check email address', 
                                   text='Email address %s is not formatted correctly' % str(email)), 400

    # Earlier we used referrer, which is problematic as it includes also URL
    # parameters. To maintain backwards compatability and to avoid doing migrations
    # check also if email is confirmed for the entire referrer
    host = flask.request.referrer
    new_host = _referrer_to_path(host)

    if not host:
        if request_wants_json():
            return jsonerror(400, {'error': "Invalid \"Referrer\" header"})
        else:
            return render_template('error.html', 
                                   title='Unable to submit form', 
                                   text='Make sure your form is running on a proper server. For geeks: could not find the "Referrer" header.'), 400

    if not EMAIL_CONFIRMED(HASH(email, host)) and not EMAIL_CONFIRMED(HASH(email, new_host)):
        return _send_confirmation(email, new_host)

    return _send_form(email, new_host)


def confirm_email(nonce):
    ''' 
    Confirmation emails point to this endpoint
    It either rejects the confirmation or
    flags associated email+host to be confirmed
    '''

    # these are used just for email_confirmed.html template
    email, host = _get_values_for_hash(nonce)

    if not VALID_NONCE(nonce):
        return render_template('error.html', 
                               title='Not a valid link', 
                               text='Confirmation token not found.<br />Please check the link and try again.'), 400
    
    else:
        REDIS.set(EMAIL_CONFIRMED_KEY(nonce), 'confirmed')
        return render_template('email_confirmed.html', email=email, host=host)


def default(template='index'):
    template = template if template.endswith('.html') else template+'.html'
    return render_template(template, is_redirect = request.args.get('redirected'))


def favicon():
    return flask.redirect(url_for('static', filename='img/favicon.ico'))

'''
Add routes and create app (create_app is called in __init__.py)

'''

def configure_routes(app):
    app.add_url_rule('/', 'index', view_func=default, methods=['GET'])
    app.add_url_rule('/favicon.ico', view_func=favicon)
    app.add_url_rule('/<email>', 'send', view_func=send, methods=['GET', 'POST'])
    app.add_url_rule('/confirm/<nonce>', 'confirm_email', view_func=confirm_email, methods=['GET'])
    app.add_url_rule('/thanks', 'thanks', view_func=thanks, methods=['GET'])
    app.add_url_rule('/<path:template>', 'default', view_func=default, methods=['GET'])


def create_app():
    app = flask.Flask('forms')
    app.config.from_object(settings)
    configure_routes(app)

    @app.errorhandler(500)
    def internal_error(e):
        import traceback
        log.error(traceback.format_exc())
        return render_template('500.html'), 500

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', title='Oops, page not found'), 404

    app.jinja_env.filters['nl2br'] = nl2br
    
    return app