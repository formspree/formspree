import datetime

from urllib.parse import urljoin

from flask import request, jsonify, g
from flask_login import current_user, login_required

from formspree import settings
from formspree.stuff import DB
from formspree.utils import jsonerror, IS_VALID_EMAIL
from .helpers import referrer_to_path, sitewide_file_check, remove_www, \
                     referrer_to_baseurl
from .models import Form, Submission, EmailTemplate


@login_required
def list():
    # grab all the forms this user controls
    if current_user.has_feature('dashboard'):
        forms = current_user.forms.order_by(Form.id.desc()).all()
    else:
        forms = []

    return jsonify({
        'ok': True,
        'user': {
            'features': {f: True for f in current_user.features},
            'email': current_user.email
        },
        'forms': [f.serialize() for f in forms]
    })


@login_required
def create():
    # check that this request came from user dashboard to prevent XSS and CSRF
    referrer = referrer_to_baseurl(request.referrer)
    service = referrer_to_baseurl(settings.SERVICE_URL)
    if referrer != service:
        return jsonerror(400, {'error': 'Improper request.'})

    if not current_user.has_feature('dashboard'):
        g.log.info('Failed to create form from dashboard. Forbidden.')
        return jsonerror(402, {'error': "Please upgrade your account."})

    email = request.get_json().get('email')
    url = request.get_json().get('url')
    sitewide = request.get_json().get('sitewide')

    g.log = g.log.bind(email=email, url=url, sitewide=sitewide)

    if not IS_VALID_EMAIL(email):
        g.log.info('Failed to create form from dashboard. Invalid address.')
        return jsonerror(400, {'error': "The provided email address is not valid."})

    g.log.info('Creating a new form from the dashboard.')

    email = email.lower().strip() # case-insensitive
    form = Form(email, owner=current_user)
    if url:
        url = 'http://' + url if not url.startswith('http') else url
        form.host = referrer_to_path(url)

        # sitewide forms, verified with a file at the root of the target domain
        if sitewide:
            if sitewide_file_check(url, email):
                form.host = remove_www(referrer_to_path(urljoin(url, '/'))[:-1])
                form.sitewide = True
            else:
                return jsonerror(403, {
                    'error': u"Couldn't verify the file at {}.".format(url)
                })

    DB.session.add(form)
    DB.session.commit()

    if form.host:
        # when the email and url are provided, we can automatically confirm the form
        # but only if the email is registered for this account
        for email in current_user.emails:
            if email.address == form.email:
                g.log.info('No need for email confirmation.')
                form.confirmed = True
                DB.session.add(form)
                DB.session.commit()
                break
        else:
            # in case the email isn't registered for this user
            # we automatically send the email confirmation
            form.send_confirmation()

    return jsonify({
        'ok': True,
        'hashid': form.hashid,
        'submission_url': settings.API_ROOT + '/' + form.hashid,
        'confirmed': form.confirmed
    })


@login_required
def get(hashid):
    if not current_user.has_feature('dashboard'):
        return jsonerror(402, {'error': "Please upgrade your account."})

    form = Form.get_with_hashid(hashid)
    if not form:
        return jsonerror(404, {'error': "Form not found."})

    if not form.controlled_by(current_user):
        return jsonerror(401, {'error': "You do not control this form."})

    submissions, fields = form.submissions_with_fields()

    ret = form.serialize()
    ret['submissions'] = submissions
    ret['fields'] = fields

    return jsonify(ret)


@login_required
def update(hashid):
    # check that this request came from user dashboard to prevent XSS and CSRF
    referrer = referrer_to_baseurl(request.referrer)
    service = referrer_to_baseurl(settings.SERVICE_URL)
    if referrer != service:
        return jsonerror(400, {'error': 'Improper request.'})

    form = Form.get_with_hashid(hashid)
    if not form:
        return jsonerror(400, {'error': 'Not a valid form.'})

    if form.owner_id != current_user.id and form not in current_user.forms:
        return jsonerror(401, {'error': 'Wrong user.'})

    patch = request.get_json()

    for attr in ['disable_storage', 'disabled', 'disable_email', 'captcha_disabled']:
        if attr in patch:
            setattr(form, attr, patch[attr])

    DB.session.add(form)
    DB.session.commit()
    return jsonify({'ok': True})


@login_required
def delete(hashid):
    # check that this request came from user dashboard to prevent XSS and CSRF
    referrer = referrer_to_baseurl(request.referrer)
    service = referrer_to_baseurl(settings.SERVICE_URL)
    if referrer != service:
        return jsonerror(400, {'error': 'Improper request.'})

    form = Form.get_with_hashid(hashid)
    if not form:
        return jsonerror(400, {'error': 'Not a valid form.'})

    if form.owner_id != current_user.id and form not in current_user.forms:
        return jsonerror(401, {'error': 'Wrong user.'})

    for submission in form.submissions:
        DB.session.delete(submission)
    DB.session.delete(form)
    DB.session.commit()

    return jsonify({'ok': True})


@login_required
def submission_delete(hashid, submissionid):
    # check that this request came from user dashboard to prevent XSS and CSRF
    referrer = referrer_to_baseurl(request.referrer)
    service = referrer_to_baseurl(settings.SERVICE_URL)
    if referrer != service:
        return jsonerror(400, {'error': 'Improper request.'})

    form = Form.get_with_hashid(hashid)
    if not form:
        return jsonerror(400, {'error': 'Not a valid form.'})

    if form.owner_id != current_user.id and form not in current_user.forms:
        return jsonerror(401, {'error': 'Wrong user.'})

    submission = Submission.query.get(submissionid)
    if not submission:
        return jsonerror(401, 'Not a valid submission.')

    DB.session.delete(submission)
    form.counter -= 1
    DB.session.add(form)
    DB.session.commit()
    return jsonify({'ok': True})


@login_required
def custom_template_set(hashid):
    form = Form.get_with_hashid(hashid)
    if not form:
        return jsonerror(404, {'error': "Form not found."})

    if not form.controlled_by(current_user):
        return jsonerror(401, {'error': "You do not control this form."})

    # TODO catch render exception before deploying
    try:
        pass
    except:
        return jsonerror(406, {'error': "Failed to render. The template has errors."})

    print(form.template)

    DB.session.add(form)
    DB.session.commit()

    return jsonify({'ok': True})


@login_required
def custom_template_preview_render():
    if not current_user.has_feature('whitelabel'):
        return jsonerror(402, {'error': "Please upgrade your account."})

    template = EmailTemplate.temporary(
        style=request.get_json()['style'],
        body=request.get_json()['body']
    )

    return template.render_body(
        data={
            'name': 'Irwin Jones',
            '_replyto': 'i.jones@example.com',
            'message': 'Hello!\n\nThis is a preview message!'
        },
        host='example.com/',
        keys=['name', '_replyto', 'message'],
        now=datetime.datetime.utcnow().strftime('%I:%M %p UTC - %d %B %Y'),
        unconfirm_url='#'
    )


@login_required
def sitewide_check():
    email = request.get_json().get('email')
    url = request.get_json().get('url')

    if sitewide_file_check(url, email):
        return jsonify({'ok': True})
    else:
        return jsonify({'ok': False})
