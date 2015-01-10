import datetime
import requests
import urlparse
import hashlib
import re
from datetime import datetime

import flask
from flask import request, url_for, render_template, redirect, jsonify, session, flash, g, abort

from flask.ext.sqlalchemy import SQLAlchemy

from sqlalchemy.exc import IntegrityError
from flask.ext.login import LoginManager, login_user, logout_user, current_user, login_required


import werkzeug.datastructures
from werkzeug.security import generate_password_hash, check_password_hash

from paste.util.multidict import MultiDict

from utils import crossdomain, request_wants_json, jsonerror

import settings

DB = SQLAlchemy()

class Form(DB.Model):
    __tablename__ = 'forms'

    id = DB.Column(DB.Integer, primary_key=True)
    hash = DB.Column(DB.String(32), unique=True)
    email = DB.Column(DB.String(120))
    host = DB.Column(DB.String(300))
    confirm_sent = DB.Column(DB.Boolean)
    confirmed = DB.Column(DB.Boolean)
    counter = DB.Column(DB.Integer)
    owner_id = DB.Column(DB.Integer, DB.ForeignKey('users.id'))

    def __init__(self, email, host, owner=None):
        self.hash = HASH(email, host)
        self.email = email
        self.host = host
        self.confirm_sent = False
        self.confirmed = False
        self.counter = 0
        self.owner = owner

class User(DB.Model):
    __tablename__ = 'users'

    id = DB.Column(DB.Integer , primary_key=True)
    email = DB.Column(DB.String(50),unique=True , index=True)
    password = DB.Column(DB.String(100))
    upgraded = DB.Column(DB.Boolean)
    registered_on = DB.Column(DB.DateTime)
    forms = DB.relationship('Form', backref='owner', lazy='dynamic')

    def __init__(self, email, password):
        self.email = email
        self.password = hash_pwd(password)
        self.upgraded = False
        self.registered_on = datetime.utcnow()

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

def hash_pwd(password):
    return generate_password_hash(password)

def check_password(password):
    return check_password_hash(hash_pwd(password), password)


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

    # We're not using referrer anymore, just the domain + path
    host = _referrer_to_path(flask.request.referrer)

    if not host:
        if request_wants_json():
            return jsonerror(400, {'error': "Invalid \"Referrer\" header"})
        else:
            return render_template('error.html',
                                   title='Unable to submit form',
                                   text='Make sure your form is running on a proper server. For geeks: could not find the "Referrer" header.'), 400

    # get the form for this request
    form = Form.query.filter_by(hash=HASH(email, host)).first()

    if form and form.confirmed:
        return _send_form(form, email, host)

    return _send_confirmation(form, email, host)


def confirm_email(nonce):
    '''
    Confirmation emails point to this endpoint
    It either rejects the confirmation or
    flags associated email+host to be confirmed
    '''

    # get the form for this request
    form = Form.query.filter_by(hash=nonce).first()

    if not form:
        return render_template('error.html',
                               title='Not a valid link',
                               text='Confirmation token not found.<br />Please check the link and try again.'), 400

    else:
        form.confirmed = True
        DB.session.add(form)
        DB.session.commit()
        return render_template('email_confirmed.html', email=form.email, host=form.host)


def default(template='index'):
    template = template if template.endswith('.html') else template+'.html'
    return render_template(template, is_redirect = request.args.get('redirected'))


def favicon():
    return flask.redirect(url_for('static', filename='img/favicon.ico'))


def configure_login(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))


def register():
    if request.method == 'GET':
        return render_template('register.html')
    try:
        user = User(request.form['email'], request.form['password'])
        DB.session.add(user)
        DB.session.commit()

    except IntegrityError:
        DB.session.rollback()
        flash("An account with this email already exists.", "error")
        return render_template('register.html')

    login_user(user)
    flash('Your account is successfully registered.')
    return redirect(url_for('dashboard'))

def login():
    if request.method == 'GET':
        return render_template('login.html')
    email = request.form['email']
    password = request.form['password']
    remember_me = False
    if 'remember_me' in request.form:
        remember_me = True
    user = User.query.filter_by(email=email).first()
    if user is None:
        flash("We can't find an account related with this Email id. Please verify the Email entered.", "error")
        return redirect(url_for('login'))
    elif not check_password(password):
        flash("Invalid Password. Please verify the password entered.")
        return redirect(url_for('login'))
    login_user(user, remember = remember_me)
    flash('Logged in successfully')
    return redirect(request.args.get('next') or url_for('dashboard'))


def logout():
    logout_user()
    return redirect(url_for('index'))


@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)


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


def _send_form(form, email, host):
    '''
    Sends request.form to user's email.
    Assumes email has been verified.
    '''

    data, keys = _form_to_dict(request.form)

    subject = data.get('_subject', 'New submission from %s' % _referrer_to_path(request.referrer))
    reply_to = data.get('_replyto', data.get('email', data.get('Email', None)))
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
        now = datetime.datetime.utcnow().strftime('%I:%M %p UTC - %d %B %Y')
        text = render_template('email/form.txt', data=data, host=host, keys=keys, now=now)
        html = render_template('email/form.html', data=data, host=host, keys=keys, now=now)
        result = _send_email(to=email,
                          subject=subject,
                          text=text,
                          html=html,
                          sender=settings.DEFAULT_SENDER,
                          reply_to=reply_to,
                          cc=cc)

        if not result[0]:
            if request_wants_json():
                return jsonerror(500, {'error': "Unable to send email"})
            else:
                return render_template('error.html',
                                       title='Unable to send email',
                                       text=result[1]), 500

        # increment the forms counter
        form.counter = Form.counter + 1
        DB.session.add(form)
        DB.session.commit()

    if request_wants_json():
        return jsonify({'success': "Email sent"})
    else:
        return redirect(next, code=302)


def _send_confirmation(form, email, host):
    '''
    Helper that actually creates confirmation nonce
    and sends the email to associated email. Renders
    different templates depending on the result
    '''
    log.debug('Sending confirmation')
    if form and form.confirm_sent:
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
                         sender=settings.DEFAULT_SENDER)

    log.debug('Sent')

    if not result[0]:
        if request_wants_json():
            return jsonerror(500, {'error': "Unable to send email"})
        else:
            return render_template('error.html',
                                   title='Unable to send email',
                                   text=result[1]), 500


    # create the form in the database and mark the email confirmation as sent
    form = form or Form(email, host)
    form.confirm_sent = True
    DB.session.add(form)
    DB.session.commit()

    if request_wants_json():
        return jsonify({'success': "confirmation email sent"})
    else:
        return render_template('confirmation_sent.html', email=email, host=host)


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

    # We're not using referrer anymore, just the domain + path
    host = _referrer_to_path(flask.request.referrer)

    if not host:
        if request_wants_json():
            return jsonerror(400, {'error': "Invalid \"Referrer\" header"})
        else:
            return render_template('error.html',
                                   title='Unable to submit form',
                                   text='Make sure your form is running on a proper server. For geeks: could not find the "Referrer" header.'), 400

    # get the form for this request
    form = Form.query.filter_by(hash=HASH(email, host)).first()

    if form and form.confirmed:
        return _send_form(form, email, host)

    return _send_confirmation(form, email, host)


def confirm_email(nonce):
    '''
    Confirmation emails point to this endpoint
    It either rejects the confirmation or
    flags associated email+host to be confirmed
    '''

    # get the form for this request
    form = Form.query.filter_by(hash=nonce).first()

    if not form:
        return render_template('error.html',
                               title='Not a valid link',
                               text='Confirmation token not found.<br />Please check the link and try again.'), 400

    else:
        form.confirmed = True
        DB.session.add(form)
        DB.session.commit()
        return render_template('email_confirmed.html', email=form.email, host=form.host)


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
    app = flask.Flask(__name__)
    app.config.from_object(settings)

    DB.init_app(app)
    configure_routes(app)

    @app.before_request
    def before_request():
        g.user = current_user

    app.jinja_env.filters['nl2br'] = lambda value: value.replace('\n','<br>\n')

    return app

