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
        flash("%s is not a valid email address." % request.form['email'], "error")
        g.log.info('Account creation failed. Invalid address.')
        return render_template('users/register.html')
    except IntegrityError:
        DB.session.rollback()
        flash("An account with this email already exists.", "error")
        g.log.info('Account creation failed. Address is use.')
        return render_template('users/register.html')

    login_user(user, remember=True)

    sent = Email.send_confirmation(user.email, user.id)
    res = redirect(request.args.get('next', url_for('account')))
    if sent:
        res.set_cookie('pending-emails', user.email, max_age=10800)
        flash("Your {SERVICE_NAME} account was created successfully!".format(**settings.__dict__), 'success')
        flash("We've sent an email confirmation to {addr}. Please go there and click on the confirmation link before you can use your {SERVICE_NAME} account.".format(addr=current_user.email, **settings.__dict__), 'info')
    else:
        flash("Your account was set up, but we couldn't send a verification email to your address, please try doing it again manually later.", "warning")
    return res


@login_required
def add_email():
    address = request.form['address'].lower().strip()
    res = redirect(url_for('account'))

    g.log = g.log.bind(address=address, account=current_user.email)

    if Email.query.get([address, current_user.id]):
        g.log.info('Failed to add email to account. Already registered.')
        flash("%s is already registered for your account." % address, 'warning')
        return res
    try:
        g.log.info('Adding new email address to account.')
        sent = Email.send_confirmation(address, current_user.id)
        if sent:
            pending = request.cookies.get('pending-emails', '').split(',')
            pending.append(address)
            res.set_cookie('pending-emails', ','.join(pending), max_age=10800)
            flash("We've sent a message with a verification link to %s." % address, 'info')
        else:
            flash("We couldn't sent you the verification email at %s. Please "
                  "try again later." % address, "error")
    except ValueError:
        flash("%s is not a valid email address." % request.form['address'], "warning")
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
            pending.remove(email.address)
            res.set_cookie('pending-emails', ','.join(pending), max_age=10800)
            flash('%s confirmed.' % email.address, 'success')
        except IntegrityError as e:
            g.log.error('Failed to save new email address to account.', exc_info=e)
            flash('A unexpected error has ocurred while we were trying to confirm the email. Please contact us if this continues to happen.', 'error')
            return res
    else:
        flash('Couldn\'t confirm %s. Wrong link.' % email, 'error')
    return res


def login():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('users/login.html')
    email = request.form['email']
    password = request.form['password']
    user = User.query.filter_by(email=email).first()
    if user is None:
        flash("We couldn't find an account related with this email. Please verify the email entered.", "warning")
        return redirect(url_for('login'))
    elif not check_password(user.password, password):
        flash("Invalid Password. Please verify the password entered.", 'warning')
        return redirect(url_for('login'))
    login_user(user, remember=True)
    flash('Logged in successfully!', 'success')
    return redirect(request.args.get('next') or url_for('dashboard'))


def logout():
    logout_user()
    return redirect(url_for('index'))


def forgot_password():
    if request.method == 'GET':
        return render_template('users/forgot.html')
    elif request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if not user:
            return render_template('error.html', title='Not registered', text="We couldn't find an account associated with this email address.</p><p>Remember that you must use the primary email address you used to register the account, it can't be any other address you have confirmed later.")

        if user.send_password_reset():
            return render_template('info.html', title='Reset email sent', text="We've sent a link to {addr}. Click on the link to be prompted to a new password.".format(addr=user.email))
        else:
            flash("Something is wrong, please report this to us.", 'error')
        return redirect(url_for('login', next=request.args.get('next')))


def reset_password(digest):
    if request.method == 'GET':
        user = User.from_password_reset(request.args['email'], digest)
        if user:
            login_user(user, remember=True)
            return render_template('users/reset.html', digest=digest)
        else:
            flash('The link you used to come to this screen has expired. Please try the reset process again.', 'error')
            return redirect(url_for('login', next=request.args.get('next')))

    elif request.method == 'POST':
        email = current_user.email # at this point the user is already logged
        user = User.from_password_reset(current_user.email, digest)
        if user and user.id == current_user.id:
            if request.form['password1'] == request.form['password2']:
                user.password = hash_pwd(request.form['password1'])
                DB.session.add(user)
                DB.session.commit()
                flash('Changed password successfully!', 'success')
                return redirect(request.args.get('next') or url_for('dashboard'))
            else:
                flash("The passwords don't match!", 'warning')
                return redirect(url_for('reset-password', digest=digest, next=request.args.get('next')))
        else:
            flash('<b>Failed to reset password</b>. The link you used to come to this screen has expired. Please try the reset process again.', 'error')
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
        g.log.warning("Couldn't charge card.", reason=e.json_body, status=e.http_status)
        flash("Sorry. Your card could not be charged. Please contact us.", "error")
        return redirect(url_for('dashboard'))

    current_user.upgraded = True
    DB.session.add(current_user)
    DB.session.commit()
    flash("Congratulations! You are now a {SERVICE_NAME} {UPGRADED_PLAN_NAME} user!".format(**settings.__dict__), 'success')
    g.log.info('Subscription created.')

    return redirect(url_for('dashboard'))

@login_required
def resubscribe():
    customer = stripe.Customer.retrieve(current_user.stripe_id)
    sub = customer.subscriptions.data[0] if customer.subscriptions.data else None

    if not sub:
        flash("You can't do this. You are not subscribed to any plan.", "warning")
        return redirect(url_for('account'))
        
    sub.plan = 'gold'
    sub.save()
    
    g.log.info('Resubscribed user.', account=current_user.email)
    flash('Glad to have you back! Your subscription will now automatically renew on {date}'.format(date=datetime.datetime.fromtimestamp(sub.current_period_end).strftime('%A, %B %d, %Y')), 'success')
    
    return redirect(url_for('account'))

@login_required
def downgrade():
    customer = stripe.Customer.retrieve(current_user.stripe_id)
    sub = customer.subscriptions.data[0] if customer.subscriptions.data else None

    if not sub:
        flash("You can't do this. You are not subscribed to any plan.", "warning")
        return redirect(url_for('account'))

    sub = sub.delete(at_period_end=True)
    flash("You were unregistered from the {SERVICE_NAME} {UPGRADED_PLAN_NAME} plan."\
        .format(**settings.__dict__), 'success')
    flash("Your card will not be charged anymore, but your plan will remain active until {date}."\
        .format(date=datetime.datetime.fromtimestamp(sub.current_period_end).strftime('%A, %B %d, %Y')),
    'info')

    g.log.info('Subscription canceled from dashboard.', account=current_user.email)
    return redirect(url_for('account'))


def stripe_webhook():
    event = request.get_json()
    g.log.info('Webhook from Stripe', type=event['type'])

    if event['type'] == 'customer.subscription.deleted':
        customer_id = event['data']['object']['customer']
        customer = stripe.Customer.retrieve(customer_id)
        if len(customer.subscriptions.data) == 0:
            user = User.query.filter_by(stripe_id=customer_id).first()
            user.upgraded = False
            DB.session.add(user)
            DB.session.commit()
            g.log.info('Downgraded user from webhook.', account=user.email)
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
            flash('That card already exists in your wallet', 'error')
        else:
            customer.sources.create(source=token)
            flash('You\'ve successfully added a new card!', 'success')
            g.log.info('Added card to stripe account.')
    except stripe.CardError as e:
        flash("Sorry, there was an error in adding your card. If this persists, please contact us.", "error")
        g.log.warning("Couldn't add card to Stripe account.", reason=e.json_body, status=e.http_status)
    except stripe.error.APIConnectionError:
        flash('We\'re unable to establish a connection with our payment processor. For your security, we haven\'t added this card to your account. Please try again later.', 'error')
        g.log.warning("Couldn't add card to Stripe account. Failed to communicate with Stripe API.")
    except stripe.error.StripeError:
        flash('Sorry, an unknown error occured. Please try again later. If this problem persists, please contact us.', 'error')
        g.log.warning("Couldn't add card to Stripe account. Unknown error.")

    return redirect(url_for('account'))


def delete_card(cardid):
    if current_user.stripe_id:
        customer = stripe.Customer.retrieve(current_user.stripe_id)
        customer.sources.retrieve(cardid).delete()
        flash('Successfully deleted card', 'success')
        g.log.info('Deleted card from account.', account=current_user.email)
    else:
        flash("That's an invalid operation", 'error')
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
