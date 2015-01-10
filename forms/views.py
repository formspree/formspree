import flask

from flask import request, url_for, render_template, redirect, jsonify
from utils import crossdomain, request_wants_json, jsonerror
from helpers import ordered_storage, referrer_to_path
from consts import IS_VALID_EMAIL, HASH
from app import app
import log

from models import Form

@app.route('/')
@app.route('/<path:template>')
def default(template='index'):
    template = template if template.endswith('.html') else template+'.html'
    return render_template(template, is_redirect = request.args.get('redirected'))

@app.errorhandler(500)
def internal_error(e):
    import traceback
    log.error(traceback.format_exc())
    return render_template('500.html'), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', title='Oops, page not found'), 404

@app.route('/thanks')
def thanks():
    return render_template('thanks.html')

@app.route('/favicon.ico')
def favicon():
    return flask.redirect(url_for('static', filename='img/favicon.ico'))

@app.route('/<email>', methods=['GET', 'POST'])
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
    host = referrer_to_path(flask.request.referrer)

    if not host:
        if request_wants_json():
            return jsonerror(400, {'error': "Invalid \"Referrer\" header"})
        else:
            return render_template('error.html',
                                   title='Unable to submit form',
                                   text='Make sure your form is running on a proper server. For geeks: could not find the "Referrer" header.'), 400

    # get the form for this request
    form = Form.query.filter_by(hash=HASH(email, host)).first()

    # If form exists and is confirmed, send email
    # otherwise send a confirmation email
    if form:
        if form.confirmed:
            status = form.send(request.form, request.referrer)
        else:
            if request_wants_json():
                return jsonify({'success': "confirmation email sent"})
            else:
                return render_template('confirmation_sent.html', email=email, host=host)
    else:
        status = Form.send_confirmation(email, host)


    # Respond to the request accordingly to the status code
    if status['code'] == Form.STATUS_EMAIL_SENT:
        return redirect(status['next'], code=302)
    elif status['code'] == Form.STATUS_EMAIL_EMPTY:
        if request_wants_json():
            return k(400, {'error': "Can't send an empty form"})
        else:
            return render_template('error.html',
                                   title='Can\'t send an empty form',
                                   text=str('<a href="%s">Return to form</a>' % request.referrer)), 400
    elif status['code'] == Form.STATUS_CONFIRMATION_SENT:
        if request_wants_json():
            return jsonify({'success': "confirmation email sent"})
        else:
            return render_template('confirmation_sent.html', email=email, host=host)


    if request_wants_json():
        return jsonerror(500, {'error': "Unable to send email"})
    else:
        return render_template('error.html',
                               title='Unable to send email',
                               text=result[1]), 500

@app.route('/confirm/<nonce>')
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
