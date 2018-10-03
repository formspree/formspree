import json
from urllib.parse import urljoin

from flask import request, render_template, redirect, \
                  jsonify, g
from flask_cors import cross_origin
from jinja2.exceptions import TemplateNotFound

from formspree import settings
from formspree.stuff import DB
from formspree.utils import request_wants_json, jsonerror, IS_VALID_EMAIL, \
                            url_domain
from formspree.forms import errors
from formspree.forms.errors import SubmitFormError
from formspree.forms.helpers import http_form_to_dict, ordered_storage, \
                                    referrer_to_path, remove_www, \
                                    verify_captcha, temp_store_hostname, \
                                    get_temp_hostname, HASH, assign_ajax, \
                                    KEYS_EXCLUDED_FROM_EMAIL
from formspree.forms.models import Form


def get_host_and_referrer(received_data):
    '''
    Looks for stored hostname in redis (from captcha).
    If it doesn't exist, uses the referer header.
    '''

    try:
        return get_temp_hostname(received_data['_host_nonce'])
    except KeyError:
        return referrer_to_path(request.referrer), request.referrer
    except ValueError as err:
        g.log.error('Invalid hostname stored on Redis.', err=err)
        raise SubmitFormError((render_template(
            'error.html',
            title='Unable to submit form',
            text='<p>We had a problem identifying to whom we should have submitted this form. '
                 'Please try submitting again. If it fails once more, please let us know at {email}</p>'.format(
                    email=settings.CONTACT_EMAIL)
        ), 500))


def validate_user_form(hashid, host):
    '''
    Gets a form from a hashid, created on the dashboard. 
    Checks to make sure the submission can be accepted by this form.
    '''

    form = Form.get_with_hashid(hashid)

    if not form:
        raise SubmitFormError(errors.bad_hashid_error(hashid))

    # Check if it has been assigned about using AJAX or not
    assign_ajax(form, request_wants_json())

    if form.disabled:
        raise SubmitFormError(errors.disabled_error())

    if not form.host:
        # add the host to the form
        # ALERT: As a side effect, sets the form's host if not already set
        form.host = host
        DB.session.add(form)
        DB.session.commit()

    # it is an error when
    #   form is not sitewide, and submission came from a different host
    #   form is sitewide, but submission came from a host rooted somewhere else, or
    elif (not form.sitewide and
          # ending slashes can be safely ignored here:
          form.host.rstrip('/') != host.rstrip('/')) \
         or (form.sitewide and \
             # removing www from both sides makes this a neutral operation:
             not remove_www(host).startswith(remove_www(form.host))):
        raise SubmitFormError(errors.mismatched_host_error(host, form))

    return form


def get_or_create_form(email, host):
    '''
    Gets the form if it already exits, otherwise checks to ensure
    that this is a valid new form submission. If so, creates a
    new form.
    '''

    form = Form.query.filter_by(hash=HASH(email, host)).first()

    if not form:

        if request_wants_json():
            # Can't create a new ajax form unless from the dashboard
            ajax_error_str = "To prevent spam, only " + \
                                settings.UPGRADED_PLAN_NAME + \
                                " accounts may create AJAX forms."
            raise SubmitFormError(jsonerror(400, {'error': ajax_error_str}))

        if url_domain(settings.SERVICE_URL) in host:
            # Bad user is trying to submit a form spoofing formspree.io
            g.log.info('User attempting to create new form spoofing SERVICE_URL. Ignoring.')
            raise SubmitFormError((render_template(
                'error.html',
                title='Unable to submit form',
                text='Sorry'), 400))

        # all good, create form
        form = Form(email, host)

    # Check if it has been assigned using AJAX or not
    assign_ajax(form, request_wants_json())

    if form.disabled:
        raise SubmitFormError(errors.disabled_error())

    return form


def check_captcha(form, email_or_string, received_data, sorted_keys):
    '''
    Checks to see if a captcha page is required, if so renders it.
    '''
    
    captcha_verified = verify_captcha(received_data, request)
    needs_captcha = not (request_wants_json() or
                            captcha_verified or
                            settings.TESTING)

    # check if captcha is disabled
    if form.has_feature('dashboard'):
        needs_captcha = needs_captcha and not form.captcha_disabled

    if needs_captcha:
        data_copy = received_data.copy()
        # Temporarily store hostname in redis while doing captcha
        nonce = temp_store_hostname(form.host, request.referrer)
        data_copy['_host_nonce'] = nonce
        action = urljoin(settings.API_ROOT, email_or_string)
        try:
            if '_language' in received_data:
                return render_template(
                    'forms/captcha_lang/{}.html'.format(received_data['_language']),
                    data=data_copy,
                    sorted_keys=sorted_keys,
                    action=action,
                    lang=received_data['_language']
                )
        except TemplateNotFound:
            g.log.error('Requested language not found for reCAPTCHA page, defaulting to English', referrer=request.referrer, lang=received_data['_language'])
            pass

        return render_template('forms/captcha.html',
                               data=data_copy,
                               sorted_keys=sorted_keys,
                               action=action,
                               lang=None)


def email_sent_success(status):
    if request_wants_json():
        return jsonify({'success': "email sent", 'next': status['next']})

    return redirect(status['next'], code=302)


def no_email_sent_success(status):
    if request_wants_json():
        return jsonify({
            'success': "no email sent, access submission archive on {} dashboard".format(settings.SERVICE_NAME), 
            'next': status['next']
        })

    return redirect(status['next'], code=302)    


def confirmation_sent_success(form, host, status):
    if request_wants_json():
        return jsonify({'success': "confirmation email sent"})

    return render_template(
        'forms/confirmation_sent.html',
        email=form.email,
        host=host,
        resend=status['code'] == Form.STATUS_CONFIRMATION_DUPLICATED
    )


def response_for_status(form, host, referrer, status):

    if status['code'] == Form.STATUS_EMAIL_SENT:
        return email_sent_success(status)

    if status['code'] == Form.STATUS_NO_EMAIL:
        return no_email_sent_success(status)

    if status['code'] == Form.STATUS_EMAIL_EMPTY:
        return errors.empty_form_error(referrer)

    if status['code'] == Form.STATUS_CONFIRMATION_SENT or \
       status['code'] == Form.STATUS_CONFIRMATION_DUPLICATED:
        return confirmation_sent_success(form, host, status)

    if status['code'] == Form.STATUS_OVERLIMIT:
        return errors.over_limit_error()

    if status['code'] == Form.STATUS_REPLYTO_ERROR:
        return errors.malformed_replyto_error(status)

    return errors.generic_send_error(send)


@cross_origin(allow_headers=['Accept', 'Content-Type',
                             'X-Requested-With', 'Authorization'])
@ordered_storage
def send(email_or_string):
    '''
    Main endpoint, finds or creates the form row from the database,
    checks validity and state of the form and sends either form data
    or verification to email.
    '''

    g.log = g.log.bind(target=email_or_string)

    if request.method == 'GET':
        return errors.bad_method_error()

    if request.form:
        received_data, sorted_keys = http_form_to_dict(request.form)
    else:
        received_data = request.get_json() or {}
        sorted_keys = received_data.keys()

    sorted_keys = [k for k in sorted_keys if k not in KEYS_EXCLUDED_FROM_EMAIL]

    try:
        # NOTE: host in this function generally refers to the referrer hostname.
        host, referrer = get_host_and_referrer(received_data)
    except SubmitFormError as vfe:
        return vfe.response

    if not host:
        return errors.no_referrer_error()

    g.log = g.log.bind(host=host, wants='json' if request_wants_json() else 'html')

    if not IS_VALID_EMAIL(email_or_string):
        # in this case it can be a hashid identifying a
        # form generated from the dashboard
        try:
            form = validate_user_form(email_or_string, host)
        except SubmitFormError as vfe:
            return vfe.response
    else:
        # in this case, it is a normal email
        try:
            form = get_or_create_form(email_or_string.lower(), host)
        except SubmitFormError as vfe:
            return vfe.response

    # If form exists and is confirmed, send email
    # otherwise send a confirmation email
    if form.confirmed:
        captcha_page = check_captcha(form, email_or_string, received_data, sorted_keys)
        if captcha_page:
            return captcha_page
        status = form.send(received_data, sorted_keys, referrer)
    else:
        status = form.send_confirmation(store_data=received_data)

    return response_for_status(form, host, referrer, status)
