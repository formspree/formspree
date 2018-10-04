import json

from flask import request, render_template, jsonify, g

from formspree import settings
from formspree.utils import request_wants_json, jsonerror


class SubmitFormError(Exception):
    def __init__(self, response):
        self.response = response


def bad_method_error():
    if request_wants_json():
        return jsonerror(405, {'error': "Please submit POST request."})

    return render_template(
        'info.html',
        title='Form should POST',
        text='Make sure your form has the <span '
             'class="code"><strong>method="POST"'
             '</strong></span> attribute'
    ), 405


def no_referrer_error():
    g.log.info('Invalid Referrer.')

    if request_wants_json():
        return jsonerror(400, {'error': "Invalid \"Referer\" header"})

    return render_template(
        'error.html',
        title='Unable to submit form',
        text='<p>Make sure you open this page through a web server, '
             'Formspree will not work in pages browsed as HTML files. '
             'Also make sure that you\'re posting to <b>{host}{path}</b>.</p>'
             '<p>For geeks: could not find the "Referer" header.</p>'.format(
                host=settings.SERVICE_URL,
                path=request.path
             )
    ), 400


def bad_hashid_error(email_or_string):
    # no form row found. it is an error.
    g.log.info('Submission rejected. No form found for this target.')
    if request_wants_json():
        return jsonerror(400, {'error': "Invalid email address"})

    return render_template(
        'error.html',
        title='Check email address',
        text='Email address %s is not formatted correctly' \
             % str(email_or_string)
    ), 400    


def disabled_error():
    # owner has disabled the form, so it should not receive any submissions
    g.log.info('submission rejected. Form is disabled.')
    if request_wants_json():
        return jsonerror(403, {'error': 'Form not active'})

    return render_template(
        'error.html',
        title='Form not active',
        text='The owner of this form has disabled this form and it is no longer accepting submissions. Your submissions was not accepted'
    ), 403


def mismatched_host_error(host, form):
    g.log.info('Submission rejected. From a different host than confirmed.')
    if request_wants_json():
        return jsonerror(403, {'error': "Submission from different host than confirmed",
                               'submitted': host, 
                               'confirmed': form.host})
    return render_template(
        'error.html',
        title='Check form address',
        text='This submission came from "%s" but the form was\
                confirmed for address "%s"' % (host, form.host)
    ), 403


def empty_form_error(referrer):
    if request_wants_json():
        return jsonerror(400, {'error': "Can't send an empty form"})

    return render_template(
        'error.html',
        title='Can\'t send an empty form',
        text=u'<p>Make sure you have placed the <a href="http://www.w3schools.com/tags/att_input_name.asp" target="_blank"><code>"name"</code> attribute</a> in all your form elements. Also, to prevent empty form submissions, take a look at the <a href="http://www.w3schools.com/tags/att_input_required.asp" target="_blank"><code>"required"</code> property</a>.</p><p>This error also happens when you have an <code>"enctype"</code> attribute set in your <code>&lt;form&gt;</code>, so make sure you don\'t.</p><p><a href="{}">Return to form</a></p>'.format(referrer)
    ), 400


def over_limit_error():
    if request_wants_json():
        return jsonify({'error': "form over quota"})

    return render_template(
        'error.html', 
        title='Form over quota', 
        text='It looks like this form is getting a lot of submissions and ran out of its quota. Try contacting this website through other means or try submitting again later.'
    ), 402


def malformed_replyto_error(status):
    if request_wants_json():
        return jsonerror(500, {'error': "_replyto or email field has not been sent correctly"})

    return render_template(
        'error.html',
        title='Invalid email address',
        text=u'You entered <span class="code">{address}</span>. That is an invalid email address. Please correct the form and try to submit again <a href="{back}">here</a>.<p style="font-size: small">This could also be a problem with the form. For example, there could be two fields with <span class="code">_replyto</span> or <span class="code">email</span> name attribute. If you suspect the form is broken, please contact the form owner and ask them to investigate</p>'''.format(address=status['address'], back=status['referrer'])
    ), 400


def generic_send_error(status):
    # error fallback -- shouldn't happen
    if request_wants_json():
        return jsonerror(500, {'error': "Unable to send email"})

    return render_template(
        'error.html',
        title='Unable to send email',
        text=u'Unable to send email. If you can, please send the link to your form and the error information to  <b>{email}</b>. And send them the following: <p><pre><code>{message}</code></pre></p>'.format(message=json.dumps(status), email=settings.CONTACT_EMAIL)
    ), 500

