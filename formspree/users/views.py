import stripe
import datetime

from flask import request, flash, url_for, render_template, redirect, g
from flask.ext.login import login_user, logout_user, \
                            current_user, login_required
from sqlalchemy.exc import IntegrityError
from helpers import check_password, hash_pwd
from formspree.app import DB
from formspree import settings
from models import User, Email
from formspree.utils import send_email


def register():
    if request.method == 'GET':
        return render_template('users/register.html')

    g.log = g.log.bind(email=request.form.get('email'))

    try:
        user = User(request.form['email'], request.form['password'])
        DB.session.add(user)
        DB.session.commit()
        g.log.info('User account created.')
    except ValueError:
        DB.session.rollback()
        flash(u"{} is not a valid email address.".format(
            request.form['email']), "error")
        g.log.info('Account creation failed. Invalid address.')
        return render_template('users/register.html')
    except IntegrityError:
        DB.session.rollback()
        flash(u"An account with this email already exists.", "error")
        g.log.info('Account creation failed. Address is already registered.')
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
def add_email():
    address = request.form['address'].lower().strip()
    res = redirect(url_for('account'))

    g.log = g.log.bind(address=address, account=current_user.email)

    if Email.query.get([address, current_user.id]):
        g.log.info('Failed to add email to account. Already registered.')
        flash(u'{} is already registered for your account.'.format(
            address), 'warning')
        return res
    try:
        g.log.info('Adding new email address to account.')
        sent = Email.send_confirmation(address, current_user.id)
        if sent:
            pending = request.cookies.get('pending-emails', '').split(',')
            pending.append(address)
            res.set_cookie('pending-emails', ','.join(pending), max_age=10800)
            flash(u"We've sent a message with a verification link to {}."
                  .format(address), 'info')
        else:
            flash(u"We couldn't sent you the verification email at {}. "
                  "Please try again later.".format(
                    address), 'error')
    except ValueError:
        flash(u'{} is not a valid email address.'.format(
            request.form['address']), 'warning')
    return res


@login_required
def confirm_email(digest):
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


def upgrade():
    token = request.form['stripeToken']

    g.log = g.log.bind(account=current_user.email)
    g.log.info('Upgrading account.')

    if not current_user:
        g.log.info('User is not logged, using email received from Stripe.', email=request.form.get('stripeEmail'))
        user = User.query.filter_by(email=request.form['stripeEmail']).first()
        login_user(user, remember=True)

    sub = None
    try:
        if current_user.stripe_id:
            g.log.info('User already has a subscription. Will change it.')
            customer = stripe.Customer.retrieve(current_user.stripe_id)
            sub = customer.subscriptions.data[0] if customer.subscriptions.data else None
        else:
            g.log.info('Will create a new subscription.')
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={'formspree_id': current_user.id},
            )
            current_user.stripe_id = customer.id

        if sub:
            sub.plan = 'gold'
            sub.source = token
            sub.save()
        else:
            customer.subscriptions.create(
                plan='gold',
                source=token
            )
    except stripe.CardError as e:
        g.log.warning("Couldn't charge card.", reason=e.json_body,
                      status=e.http_status)
        flash(u"Sorry. Your card could not be charged. Please contact us.",
              "error")
        return redirect(url_for('dashboard'))

    current_user.upgraded = True
    DB.session.add(current_user)
    DB.session.commit()
    flash(u"Congratulations! You are now a {SERVICE_NAME} "
          "{UPGRADED_PLAN_NAME} user!".format(**settings.__dict__),
          'success')
    g.log.info('Subscription created.')

    return redirect(url_for('dashboard'))


@login_required
def resubscribe():
    customer = stripe.Customer.retrieve(current_user.stripe_id)
    sub = customer.subscriptions.data[0] if customer.subscriptions.data else None

    if not sub:
        flash(u"You can't do this. You are not subscribed to any plan.",
              "warning")
        return redirect(url_for('account'))

    sub.plan = 'gold'
    sub.save()

    g.log.info('Resubscribed user.', account=current_user.email)
    at = datetime.datetime.fromtimestamp(sub.current_period_end)
    flash(u'Glad to have you back! Your subscription will now automatically '
          'renew on {date}'.format(date=at.strftime('%A, %B %d, %Y')),
          'success')

    return redirect(url_for('account'))


@login_required
def downgrade():
    customer = stripe.Customer.retrieve(current_user.stripe_id)
    sub = customer.subscriptions.data[0] if customer.subscriptions.data else None

    if not sub:
        flash(u"You can't do this. You are not subscribed to any plan.",
              "warning")
        return redirect(url_for('account'))

    sub = sub.delete(at_period_end=True)
    flash(u"You were unregistered from the {SERVICE_NAME} "
          "{UPGRADED_PLAN_NAME} plan.".format(**settings.__dict__),
          'success')
    at = datetime.datetime.fromtimestamp(sub.current_period_end)
    flash(u"Your card will not be charged anymore, but your plan will "
          "remain active until {date}.".format(
            date=at.strftime('%A, %B %d, %Y')
          ), 'info')

    g.log.info('Subscription canceled from dashboard.', account=current_user.email)
    return redirect(url_for('account'))


def stripe_webhook():
    event = request.get_json()
    g.log.info('Webhook from Stripe', type=event['type'])

    try:
        if event['type'] == 'customer.subscription.deleted': # User subscription has expired
            customer_id = event['data']['object']['customer']
            customer = stripe.Customer.retrieve(customer_id)
            if len(customer.subscriptions.data) == 0:
                user = User.query.filter_by(stripe_id=customer_id).first()
                user.upgraded = False
                DB.session.add(user)
                DB.session.commit()
                g.log.info('Downgraded user from webhook.', account=user.email)
                send_email(to=customer.email,
                           subject='Successfully Downgraded from {} {}'.format(settings.SERVICE_NAME, settings.UPGRADED_PLAN_NAME),
                           text=render_template('email/downgraded.txt'),
                           html=render_template('email/downgraded.html'),
                           sender=settings.DEFAULT_SENDER)
        elif event['type'] == 'invoice.payment_failed': # User payment failed
            customer_id = event['data']['object']['customer']
            customer = stripe.Customer.retrieve(customer_id)
            g.log.info('User payment failed', account=customer.email)
            send_email(to=customer.email,
                       subject='[ACTION REQUIRED] Failed Payment for {} {}'.format(settings.SERVICE_NAME,
                                                                           settings.UPGRADED_PLAN_NAME),
                       text=render_template('email/payment-failed.txt'),
                       html=render_template('email/payment-failed.html'),
                       sender=settings.DEFAULT_SENDER)
    except Exception as e:
        g.log.error('Webhook failed for customer', json=event, error=e)
        return 'Failure, developer please check logs', 500
    return 'ok'


@login_required
def add_card():
    token = request.form['stripeToken']

    g.log = g.log.bind(account=current_user.email)

    try:
        if current_user.stripe_id:
            customer = stripe.Customer.retrieve(current_user.stripe_id)
        else:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={'formspree_id': current_user.id},
            )
            current_user.stripe_id = customer.id
        # Make sure this card doesn't already exist
        new_fingerprint = stripe.Token.retrieve(token).card.fingerprint
        if new_fingerprint in (card.fingerprint for card in customer.sources.all(object='card').data):
            flash(u'That card already exists in your wallet', 'error')
        else:
            customer.sources.create(source=token)
            flash(u"You've successfully added a new card!", 'success')
            g.log.info('Added card to stripe account.')
    except stripe.CardError as e:
        flash(u"Sorry, there was an error in adding your card. If this "
              "persists, please contact us.", "error")
        g.log.warning("Couldn't add card to Stripe account.",
                      reason=e.json_body, status=e.http_status)
    except stripe.error.APIConnectionError:
        flash(u"We're unable to establish a connection with our payment "
              "processor. For your security, we haven't added this "
              "card to your account. Please try again later.", 'error')
        g.log.warning("Couldn't add card to Stripe account. Failed to "
                      "communicate with Stripe API.")
    except stripe.error.StripeError:
        flash(u'Sorry, an unknown error occured. Please try again '
              'later. If this problem persists, please contact us.', 'error')
        g.log.warning("Couldn't add card to Stripe account. Unknown error.")

    return redirect(url_for('account'))

@login_required
def change_default_card(cardid):
    try:
        customer = stripe.Customer.retrieve(current_user.stripe_id)
        customer.default_source = cardid
        customer.save()
        card = customer.sources.retrieve(cardid)
        flash("Successfully changed default payment source to your {} ending in {}".format(card.brand, card.last4), "success")
    except Exception as e:
        flash(u"Sorry something went wrong. If this error persists, please contact support", 'error')
        g.log.warning("Failed to change default card", account=current_user.email, card=cardid)
    return redirect(url_for('account'))

@login_required
def delete_card(cardid):
    if current_user.stripe_id:
        customer = stripe.Customer.retrieve(current_user.stripe_id)
        customer.sources.retrieve(cardid).delete()
        flash(u'Successfully deleted card', 'success')
        g.log.info('Deleted card from account.', account=current_user.email)
    else:
        flash(u"That's an invalid operation", 'error')
    return redirect(url_for('account'))


@login_required
def account():
    emails = {
        'verified': (e.address for e in current_user.emails.order_by(Email.registered_on.desc())),
        'pending': filter(bool, request.cookies.get('pending-emails', '').split(',')),
    }
    sub = None
    cards = {}
    if current_user.stripe_id:
        try:
            customer = stripe.Customer.retrieve(current_user.stripe_id)
            card_mappings = {
                'Visa': 'cc-visa',
                'American Express': 'cc-amex',
                'MasterCard': 'cc-mastercard',
                'Discover': 'cc-discover',
                'JCB': 'cc-jcb',
                'Diners Club': 'cc-diners-club',
                'Unknown': 'credit-card'
            }
            cards = customer.sources.all(object='card').data
            for card in cards:
                if customer.default_source == card.id:
                    card.default = True
                card.css_name = card_mappings[card.brand]
            sub = customer.subscriptions.data[0] if customer.subscriptions.data else None
            if sub:
                sub.current_period_end = datetime.datetime.fromtimestamp(sub.current_period_end).strftime('%A, %B %d, %Y')
        except stripe.error.StripeError:
            return render_template('error.html', title='Unable to connect', text="We're unable to make a secure connection to verify your account details. Please try again in a little bit. If this problem persists, please contact <strong>%s</strong>" % settings.CONTACT_EMAIL)
    return render_template('users/account.html', emails=emails, cards=cards, sub=sub)

@login_required
def billing():
    if current_user.stripe_id:
        try:
            customer = stripe.Customer.retrieve(current_user.stripe_id)
            card_mappings = {
                'Visa': 'cc-visa',
                'American Express': 'cc-amex',
                'MasterCard': 'cc-mastercard',
                'Discover': 'cc-discover',
                'JCB': 'cc-jcb',
                'Diners Club': 'cc-diners-club',
                'Unknown': 'credit-card'
            }
            cards = customer.sources.all(object='card').data
            for card in cards:
                if customer.default_source == card.id:
                    card.default = True
                card.css_name = card_mappings[card.brand]
            sub = customer.subscriptions.data[0] if customer.subscriptions.data else None
            if sub:
                sub.current_period_end = datetime.datetime.fromtimestamp(sub.current_period_end).strftime('%A, %B %d, %Y')
        except stripe.error.StripeError:
            return render_template('error.html', title='Unable to connect', text="We're unable to make a secure connection to verify your account details. Please try again in a little bit. If this problem persists, please contact <strong>%s</strong>" % settings.CONTACT_EMAIL)

        invoices = stripe.Invoice.list(customer=customer, limit=12)
        return render_template('users/billing.html', cards=cards, sub=sub, invoices=invoices)

@login_required
def update_invoice_address():
    new_address = request.form.get('invoice-address')
    if len(new_address) == 0:
        new_address = None
    user = User.query.filter_by(email=current_user.email).first()
    user.invoice_address = new_address

    DB.session.add(user)
    DB.session.commit()
    flash('Successfully updated invoicing address', 'success')
    return redirect(url_for('billing-dashboard'))


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
        card_mappings = {
            'Visa': 'cc-visa',
            'American Express': 'cc-amex',
            'MasterCard': 'cc-mastercard',
            'Discover': 'cc-discover',
            'JCB': 'cc-jcb',
            'Diners Club': 'cc-diners-club',
            'Unknown': 'credit-card'
        }
        charge.source.css_name = card_mappings[charge.source.brand]
        return render_template('users/invoice.html', invoice=invoice, charge=charge)
    return render_template('users/invoice.html', invoice=invoice)