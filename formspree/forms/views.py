import flask

from flask import request, url_for, render_template, redirect, jsonify, flash
from flask.ext.login import current_user, login_required
from flask.ext.cors import cross_origin
from formspree.utils import request_wants_json, jsonerror, IS_VALID_EMAIL
from helpers import ordered_storage, referrer_to_path, HASH, EXCLUDE_KEYS

from formspree.app import DB
from models import Form, Submission
from formspree import settings

def thanks():
    return render_template('forms/thanks.html')

@cross_origin(allow_headers=['Accept', 'Content-Type', 'X-Requested-With'])
@ordered_storage
def send(email_or_string):
    '''
    Main endpoint, finds or creates the form row from the database,
    checks validity and state of the form and sends either form data
    or verification to email.
    '''

    if request.method == 'GET':
        if request_wants_json():
            return jsonerror(405, {'error': "Please submit POST request."})
        else:
            return render_template('info.html',
                                   title='Form should POST',
                                   text='Make sure your form has the <span class="code"><strong>method="POST"</strong></span> attribute'), 405

    host = referrer_to_path(flask.request.referrer)
    if not host:
        if request_wants_json():
            return jsonerror(400, {'error': "Invalid \"Referrer\" header"})
        else:
            return render_template('error.html',
                                   title='Unable to submit form',
                                   text='Make sure your form is running on a proper server. For geeks: could not find the "Referrer" header.'), 400

    if not IS_VALID_EMAIL(email_or_string):
        # in this case it can be a random_like_string identifying a
        # form generated from the dashboard
        random_like_string = email_or_string
        form = Form.get_form_by_random_like_string(random_like_string)

        if form:
            email = form.email

            if not form.host:
                # add the host to the form
                form.host = host
                DB.session.add(form)
                DB.session.commit()
            elif form.host != host:
                # if the form submission came from a different host, it is an error
                if request_wants_json():
                    return jsonerror(403, {'error': "Submission from different host than confirmed",
                                           'submitted': host, 'confirmed': form.host})
                else:
                    return render_template('error.html',
                                           title='Check form address',
                                           text='This submission came from "%s" but the form was\
                                                 confirmed for the address "%s"' % (host, form.host)), 403
        else:
            # no form row found. it is an error.
            if request_wants_json():
                return jsonerror(400, {'error': "Invalid email address"})
            else:
                return render_template('error.html',
                                       title='Check email address',
                                       text='Email address %s is not formatted correctly' \
                                            % str(email_or_string)), 400
    else:
        # in this case, it is a normal email
        email = email_or_string

        # get the form for this request
        form = Form.query.filter_by(hash=HASH(email, host)).first() \
               or Form(email, host) # or create it if it doesn't exists

    # If form exists and is confirmed, send email
    # otherwise send a confirmation email
    if form.confirmed:
        status = form.send(request.form, request.referrer)
    else:
        status = form.send_confirmation()

    # Respond to the request accordingly to the status code
    if status['code'] == Form.STATUS_EMAIL_SENT:
        if request_wants_json():
            return jsonify({ 'success': "email sent", 'next': status['next'] })
        else:
            return redirect(status['next'], code=302)
    elif status['code'] == Form.STATUS_EMAIL_EMPTY:
        if request_wants_json():
            return jsonerror(400, {'error': "Can't send an empty form"})
        else:
            return render_template('error.html',
                                   title='Can\'t send an empty form',
                                   text=str('<a href="%s">Return to form</a>' % request.referrer)), 400
    elif status['code'] == Form.STATUS_CONFIRMATION_SENT or \
         status['code'] == Form.STATUS_CONFIRMATION_DUPLICATED:
        if request_wants_json():
            return jsonify({'success': "confirmation email sent"})
        else:
            return render_template('forms/confirmation_sent.html', email=email, host=host)

    if request_wants_json():
        return jsonerror(500, {'error': "Unable to send email"})
    else:
        return render_template('error.html',
                               title='Unable to send email',
                               text='Unable to send email'), 500


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


@login_required
def forms():
    if request.method == 'GET':
        if request_wants_json():
            return jsonerror(501, {'error': "This endpoint may return the list of forms for the logged user."})
        else:
            return redirect(url_for('dashboard'))

    # Create a new form
    if not current_user.upgraded:
        return jsonerror(402, {'error': "Please upgrade your account."})

    if request.get_json():
        email = request.get_json().get('email')
    else:
        email = request.form.get('email')

    if not IS_VALID_EMAIL(email):
        if request_wants_json():
            return jsonerror(400, {'error': "The email you sent is not a valid email."})
        else:
            flash('The email you sent is not a valid email.', 'error')
            return redirect(url_for('dashboard'))

    form = Form(email, owner=current_user)
    DB.session.add(form)
    DB.session.commit()

    # A unique identifier for the form that maps to its id,
    # but doesn't seem like a sequential integer
    random_like_string = form.get_random_like_string()

    if request_wants_json():
        return jsonify({
            'ok': True,
            'random_like_string': random_like_string,
            'submission_url': settings.API_ROOT + '/' + random_like_string
        })
    else:
        return redirect(url_for('dashboard'))

@login_required
def form_submissions(random_like_string):
    if not current_user.upgraded:
        return jsonerror(402, {'error': "Please upgrade your account."})

    form = Form.get_form_by_random_like_string(random_like_string)
    submissions = form.submissions

    if request_wants_json():
        if current_user.id != form.owner_id:
            return jsonerror(403, {'error': "You're not the owner of this form."})

        return jsonify({
            'submissions': [s.data for s in submissions]
        })
    else:
        if current_user.id != form.owner_id:
            return redirect(url_for('dashboard'))

        fields = set()
        for s in submissions:
            fields.update(s.data.keys())
        fields -= set(EXCLUDE_KEYS)

        return render_template('forms/submissions.html',
            form=form,
            fields=sorted(fields),
            submissions=submissions
        )
