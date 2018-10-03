import json
import datetime
import io

import requests
import unicodecsv as csv
from lxml.html import rewrite_links

from flask import request, url_for, render_template, \
                  jsonify, make_response, Response, g, \
                  session, abort, render_template_string
from flask_login import current_user, login_required

from formspree import settings
from formspree.stuff import DB, TEMPLATES
from formspree.utils import request_wants_json, jsonerror, \
                            valid_url, send_email
from formspree.forms.helpers import verify_captcha, HASH
from formspree.forms.models import Form, EmailTemplate


def thanks():
    if request.args.get('next') and not valid_url(request.args.get('next')):
        return render_template('error.html',
            title='Invalid URL', text='An invalid URL was supplied'), 400
    return render_template('forms/thanks.html', next=request.args.get('next'))


def resend_confirmation(email):
    g.log = g.log.bind(email=email, host=request.form.get('host'))
    g.log.info('Resending confirmation.')

    if verify_captcha(request.form, request):
        # check if this email is listed on SendGrid's bounces
        r = requests.get('https://api.sendgrid.com/api/bounces.get.json',
            params={
                'email': email,
                'api_user': settings.SENDGRID_USERNAME,
                'api_key': settings.SENDGRID_PASSWORD
            }
        )
        if r.ok and len(r.json()) and 'reason' in r.json()[0]:
            # tell the user to verify his mailbox
            reason = r.json()[0]['reason']
            g.log.info('Email is blocked on SendGrid. Telling the user.')
            if request_wants_json():
                resp = jsonify({'error': "Verify your mailbox, we can't reach it.", 'reason': reason})
            else:
                resp = make_response(render_template('info.html',
                    title='Verify the availability of your mailbox',
                    text="We encountered an error when trying to deliver the confirmation message to <b>" + email + "</b> at the first time we tried. For spam reasons, we will not try again until we are sure the problem is fixed. Here's the reason:</p><p><center><i>" + reason + "</i></center></p><p>Please make sure this problem is not happening still, then go to <a href='/unblock/" + email + "'>this page</a> to unblock your address.</p><p>After you have unblocked the address, please try to resend the confirmation again.</p>"
                ))
            return resp
        # ~~~
        # if there's no bounce, we proceed to resend the confirmation.

        # BUG: What if this is an owned form with hashid??

        form = Form.query.filter_by(hash=HASH(email, request.form['host'])).first()
        if not form:
            if request_wants_json():
                return jsonerror(400, {'error': "This form does not exist."})
            else:
                return render_template('error.html',
                                       title='Check email address',
                                       text='This form does not exist.'), 400
        form.confirm_sent = False
        status = form.send_confirmation()
        if status['code'] == Form.STATUS_CONFIRMATION_SENT:
            if request_wants_json():
                return jsonify({'success': "confirmation email sent"})
            else:
                return render_template('forms/confirmation_sent.html',
                    email=email,
                    host=request.form['host'],
                    resend=status['code'] == Form.STATUS_CONFIRMATION_DUPLICATED
                )

    # fallback response -- should happen only when the recaptcha is failed.
    g.log.warning('Failed to resend confirmation.')
    return render_template('error.html',
                           title='Unable to send email',
                           text='Please make sure you pass the <i>reCaptcha</i> test before submitting.'), 500


def unblock_email(email):
    if request.method == 'POST':
        g.log = g.log.bind(email=email)
        g.log.info('Unblocking email on SendGrid.')

        if verify_captcha(request.form, request):
            # clear the bounce from SendGrid
            r = requests.post(
                'https://api.sendgrid.com/api/bounces.delete.json',
                data={
                    'email': email,
                    'api_user': settings.SENDGRID_USERNAME,
                    'api_key': settings.SENDGRID_PASSWORD
                }
            )
            if r.ok and r.json()['message'] == 'success':
                g.log.info('Unblocked address.')
                return render_template('info.html',
                                       title='Successfully unblocked email address!',
                                       text='You should be able to receive emails from Formspree again.')
            else:
                g.log.warning('Failed to unblock email on SendGrid.')
                return render_template('error.html',
                                       title='Failed to unblock address.',
                                       text=email + ' is not a valid address or wasn\'t blocked on our side.')

        # fallback response -- should happen only when the recaptcha is failed.
        g.log.warning('Failed to unblock email. reCaptcha test failed.')
        return render_template('error.html',
            title='Unable to unblock email',
            text='Please make sure you pass the <i>reCaptcha</i> test before '
                 'submitting.'), 500

    elif request.method == 'GET':
        return render_template('forms/unblock_email.html', email=email), 200


def request_unconfirm_form(form_id):
    '''
    This endpoints triggers a confirmation email that directs users to the
    GET version of unconfirm_form.
    '''

    # repel bots
    if not request.user_agent.browser:
        return ''

    form = Form.query.get(form_id)

    unconfirm_url = url_for(
        'unconfirm_form',
        form_id=form.id,
        digest=form.unconfirm_digest(),
        _external=True
    )
    send_email(
        to=form.email,
        subject='Unsubscribe from form at {}'.format(form.host),
        html=render_template_string(TEMPLATES.get('unsubscribe-confirmation.html'),
                                    url=unconfirm_url,
                                    email=form.email,
                                    host=form.host),
        text=render_template('email/unsubscribe-confirmation.txt',
            url=unconfirm_url,
            email=form.email,
            host=form.host),
        sender=settings.DEFAULT_SENDER,
    )

    return render_template('info.html',
        title='Link sent to your address',
        text="We've sent an email to {} with a link to finish "
             "unsubscribing.".format(form.email)), 200
    

def unconfirm_form(form_id, digest):
    '''
    Here we check the digest for a form and handle the unconfirmation.
    Also works for List-Unsubscribe triggered POSTs.
    When GET, give the user the option to unsubscribe from other forms as well.
    '''
    form = Form.query.get(form_id)
    success = form.unconfirm_with_digest(digest)

    if request.method == 'GET':
        if success:
            other_forms = Form.query.filter_by(confirmed=True, email=form.email)

            session['unconfirming'] = form.email

            return render_template('forms/unconfirm.html',
                other_forms=other_forms,
                disabled_form=form
            ), 200
        else:
            return render_template('error.html',
                title='Not a valid link',
                text='This unconfirmation link is not valid.'), 400

    if request.method == 'POST':
        if success:
            return '', 200
        else:
            return abort(401)


def unconfirm_multiple():
    unconfirming_for_email = session.get('unconfirming')
    if not unconfirming_for_email:
        return render_template('error.html',
            title='Forbidden',
            text="You're not allowed to unconfirm these forms."), 401

    for form_id in request.form.getlist('form_ids'):
        form = Form.query.get(form_id)
        if form.email == unconfirming_for_email:
            form.confirmed = False
            DB.session.add(form)
    DB.session.commit()

    return render_template('info.html',
        title='Success',
        text='The selected forms were unconfirmed successfully.'), 200


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
def serve_dashboard(hashid=None, s=None):
    return render_template('forms/dashboard.html')


@login_required
def custom_template_preview_render():
    body, _ = EmailTemplate.make_sample(
        from_name=request.args.get('from_name'),
        subject=request.args.get('subject'),
        style=request.args.get('style'),
        body=request.args.get('body'),
    )

    return rewrite_links(body, lambda x: "#" + x)


@login_required
def export_submissions(hashid, format=None):
    if not current_user.has_feature('dashboard'):
        return jsonerror(402, {'error': "Please upgrade your account."})

    form = Form.get_with_hashid(hashid)
    if not form.controlled_by(current_user):
        return abort(401)

    submissions, fields = form.submissions_with_fields()

    if format == 'json':
        return Response(
            json.dumps({
                'host': form.host,
                'email': form.email,
                'fields': fields,
                'submissions': submissions
            }, sort_keys=True, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': 'attachment; filename=form-%s-submissions-%s.json' \
                            % (hashid, datetime.datetime.now().isoformat().split('.')[0])
            }
        )
    elif format == 'csv':
        out = io.BytesIO()
        
        w = csv.DictWriter(out, fieldnames=['id'] + fields, encoding='utf-8')
        w.writeheader()
        for sub in submissions:
            w.writerow(sub)

        return Response(
            out.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=form-%s-submissions-%s.csv' \
                            % (hashid, datetime.datetime.now().isoformat().split('.')[0])
            }
        )
