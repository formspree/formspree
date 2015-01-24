import flask

from flask import request, url_for, render_template, redirect, jsonify
from formspree.utils import crossdomain, request_wants_json, jsonerror
from formspree import log
from helpers import ordered_storage, referrer_to_path, IS_VALID_EMAIL, HASH

from models import Form

def thanks():
    return render_template('forms/thanks.html')

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
                return render_template('forms/confirmation_sent.html', email=email, host=host)
    else:
        status = Form.send_confirmation(email, host)


    # Respond to the request accordingly to the status code
    if status['code'] == Form.STATUS_EMAIL_SENT:
        if request_wants_json():
            return jsonify({ 'success': "email sent", 'next': status['next'] })
        else:
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
            return render_template('forms/confirmation_sent.html', email=email, host=host)

    if request_wants_json():
        return jsonerror(500, {'error': "Unable to send email"})
    else:
        return render_template('error.html', title='Unable to send email'), 500

def confirm_email(nonce):
    '''
    Confirmation emails point to this endpoint
    It either rejects the confirmation or
    flags associated email+host to be confirmed
    '''

    # get the form for this request
    form = Form.confirm(nonce)

    if not form:
        return render_template('error.html',
                               title='Not a valid link',
                               text='Confirmation token not found.<br />Please check the link and try again.'), 400

    else:
        return render_template('forms/email_confirmed.html', email=form.email, host=form.host)
