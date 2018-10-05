import stripe
import datetime

from flask import request, flash, url_for, render_template, \
                  render_template_string, redirect, g
from flask_login import login_user, logout_user, \
                            current_user, login_required
from sqlalchemy.exc import IntegrityError

from formspree import settings
from formspree.stuff import DB, TEMPLATES
from formspree.utils import send_email
from .models import User, Email, Plan
from .helpers import check_password, hash_pwd, send_downgrade_email, \
                     CARD_MAPPINGS


def register():
    if request.method == 'GET':
        return render_template('users/register.html')

    g.log = g.log.bind(email=request.form.get('email'))

    try:
        user = User.register(request.form['email'], request.form['password'])
        g.log.info('User created.', ip=request.headers.get('X-Forwarded-For'))
    except ValueError:
        flash(u"{} is not a valid email address.".format(
            request.form['email']), "error")
        g.log.info('Account creation failed. Invalid address.',
            ip=request.headers.get('X-Forwarded-For'))
        return render_template('users/register.html')

    login_user(user, remember=True)

    sent = Email.send_confirmation(user.email, user.id)
    res = redirect(request.args.get('next', url_for('account')))
    if sent:
        res.set_cookie('pending-emails', user.email, max_age=10800)
        flash(u"Your {SERVICE_NAME} account was created successfully!".format(
            **settings.__dict__), 'success')
        flash(u"We've sent an email confirmation to {addr}. Please go there "
              "and click on the confirmation link before you can use your "
              "{SERVICE_NAME} account.".format(
                addr=current_user.email,
                **settings.__dict__), 'info')
    else:
        flash(u"Your account was set up, but we couldn't send a verification "
              "email to your address, please try doing it again manually "
              "later.", 'warning')
    return res


@login_required
def confirm_account_email(digest):
    res = redirect(url_for('account'))
    email = Email.create_with_digest(addr=request.args.get('email', ''),
                                     user_id=current_user.id,
                                     digest=digest)
    if email:
        try:
            DB.session.add(email)
            DB.session.commit()
            pending = request.cookies.get('pending-emails', '').split(',')
            try:
                pending.remove(email.address)
            except ValueError:
                pass  # when not in list, means nothing serious.
            res.set_cookie('pending-emails', ','.join(pending), max_age=10800)
            flash(u'{} confirmed.'.format(
                email.address), 'success')
        except IntegrityError as e:
            g.log.error('Failed to save new email address to account.',
                        exception=repr(e))
            flash(u'A unexpected error has ocurred while we were trying '
                  'to confirm the email. Please contact us if this continues '
                  'to happen.', 'error')
            return res
    else:
        flash(u"Couldn't confirm {}. Wrong link.".format(email), 'error')
    return res


def login():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('users/login.html')
    email = request.form['email'].lower().strip()
    password = request.form['password']
    user = User.query.filter_by(email=email).first()
    if user is None or not check_password(user.password, password):
        flash(u"Invalid username or password.",
              'warning')
        return redirect(url_for('login'))
    login_user(user, remember=True)
    g.log.info('Logged user in', user=user.email, ip=request.headers.get('X-Forwarded-For'))
    flash(u'Logged in successfully!', 'success')
    return redirect(request.args.get('next') or url_for('dashboard'))


def logout():
    logout_user()
    return redirect(url_for('index'))


def forgot_password():
    if request.method == 'GET':
        return render_template('users/forgot.html')
    elif request.method == 'POST':
        email = request.form['email'].lower().strip()
        user = User.query.filter_by(email=email).first()
        if not user or user.send_password_reset():
            return render_template(
                'info.html',
                title='Reset email sent',
                text=u"We've sent you a password reset link. Please check your email."
            )
        else:
            flash(u"Something is wrong, please report this to us.", 'error')
        return redirect(url_for('login', next=request.args.get('next')))


def reset_password(digest):
    if request.method == 'GET':
        email = request.args['email'].lower().strip()
        user = User.from_password_reset(email, digest)
        if user:
            login_user(user, remember=True)
            return render_template('users/reset.html', digest=digest)
        else:
            flash(u'The link you used to come to this screen has expired. '
                  'Please try the reset process again.', 'error')
            return redirect(url_for('login', next=request.args.get('next')))

    elif request.method == 'POST':
        user = User.from_password_reset(current_user.email, digest)
        if user and user.id == current_user.id:
            if request.form['password1'] == request.form['password2']:
                user.password = hash_pwd(request.form['password1'])
                DB.session.add(user)
                DB.session.commit()
                flash(u'Changed password successfully!', 'success')
                return redirect(request.args.get('next') or url_for('dashboard'))
            else:
                flash(u"The passwords don't match!", 'warning')
                return redirect(url_for('reset-password', digest=digest, next=request.args.get('next')))
        else:
            flash(u'<b>Failed to reset password</b>. The link you used '
                  'to come to this screen has expired. Please try the reset '
                  'process again.', 'error')
            return redirect(url_for('login', next=request.args.get('next')))


def stripe_webhook():
    payload = request.data.decode('utf-8')
    g.log.info('Received webhook from Stripe')

    sig_header = request.headers.get('STRIPE_SIGNATURE')
    event = None

    try:
        if settings.TESTING:
            event = request.get_json()
        else:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        if event['type'] == 'customer.subscription.deleted':  # User subscription has expired
            customer_id = event['data']['object']['customer']
            customer = stripe.Customer.retrieve(customer_id)
            if len(customer.subscriptions.data) == 0:
                user = User.query.filter_by(stripe_id=customer_id).first()
                user.plan = Plan.free
                DB.session.add(user)
                DB.session.commit()
                g.log.info('Downgraded user from webhook.', account=user.email)
                send_downgrade_email.delay(user.email)
        elif event['type'] == 'invoice.payment_failed':  # User payment failed
            customer_id = event['data']['object']['customer']
            customer = stripe.Customer.retrieve(customer_id)
            g.log.info('User payment failed', account=customer.email)
            send_email(to=customer.email,
                       subject='[ACTION REQUIRED] Failed Payment for {} {}'.format(
                           settings.SERVICE_NAME,
                           settings.UPGRADED_PLAN_NAME
                       ),
                       text=render_template('email/payment-failed.txt'),
                       html=render_template_string(TEMPLATES.get('payment-failed.html')),
                       sender=settings.DEFAULT_SENDER)
        return 'ok'
    except ValueError as e:
        g.log.error('Webhook failed for customer', json=event, error=e)
        return 'Failure, developer please check logs', 500
    except stripe.error.SignatureVerificationError as e:
        g.log.error('Webhook failed Stripe signature verification', json=event, error=e)
        return '', 400
    except Exception as e:
        g.log.error('Webhook failed for unknown reason', json=event, error=e)
        return '', 500


@login_required
def invoice(invoice_id):
    invoice = stripe.Invoice.retrieve('in_' + invoice_id)
    if invoice.customer != current_user.stripe_id:
        return render_template(
            'error.html',
            title='Unauthorized Invoice',
            text='Only the account owner can open this invoice'
        ), 403
    if invoice.charge:
        charge = stripe.Charge.retrieve(invoice.charge)
        charge.source.css_name = CARD_MAPPINGS[charge.source.card.brand]
        return render_template('users/invoice.html', invoice=invoice, charge=charge)
    return render_template('users/invoice.html', invoice=invoice)
