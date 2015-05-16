import stripe
import datetime

from flask import request, flash, url_for, render_template, redirect, abort
from flask.ext.login import login_user, logout_user, current_user, login_required
from sqlalchemy.exc import IntegrityError
from helpers import check_password
from formspree.app import DB
from formspree import settings
from models import User, Email

def register():
    if request.method == 'GET':
        return render_template('users/register.html')
    try:
        user = User(request.form['email'], request.form['password'])
        DB.session.add(user)
        DB.session.commit()
    except ValueError:
        DB.session.rollback()
        flash("%s is not a valid email address." % request.form['email'], "error")
        return render_template('users/register.html')
    except IntegrityError:
        DB.session.rollback()
        flash("An account with this email already exists.", "error")
        return render_template('users/register.html')

    login_user(user)

    sent = Email.send_confirmation(user.email, user.id)
    if sent:
        res = redirect(url_for('notify-email-confirmation'))
        res.set_cookie('pending-emails', user.email, max_age=10800)
        flash('Your Formspree account was created successfully!', 'success')
        return res
    else:
        flash("Your account was set up, but we couldn't send a verification email "
              "to your address, please try doing it again manually later.", "warning")
        return redirect(url_for('account'))

@login_required
def add_email():
    address = request.form['address']
    res = redirect(url_for('account'))

    if Email.query.get([address, current_user.id]):
        flash("%s is already registered for your account." % address, 'warning')
        return res
    try:
        sent = Email.send_confirmation(address, current_user.id)
        if sent:
            pending = request.cookies.get('pending-emails', '').split(',')
            pending.append(address)
            res.set_cookie('pending-emails', ','.join(pending), max_age=10800)
            flash("We've sent a message with a verification link to %s." % address, 'info')
        else:
            flash("We couldn't sent you the verification email at %s. Please "
                  "try again later.", "error")
    except ValueError:
        flash("%s is not a valid email address." % request.form['email'], "warning")
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
        except IntegrityError:
            return res
    else:
        flash('Couldn\'t confirm %s. Wrong link.' % email, 'error')
    return res


def login():
    if request.method == 'GET':
        if current_user.is_authenticated():
            return redirect(url_for('dashboard'))
        return render_template('users/login.html')
    email = request.form['email']
    password = request.form['password']
    remember_me = False
    if 'remember_me' in request.form:
        remember_me = True
    user = User.query.filter_by(email=email).first()
    if user is None:
        flash("We couldn't find an account related with this email. Please verify the email entered.", "warning")
        return redirect(url_for('login'))
    elif not check_password(user.password, password):
        flash("Invalid Password. Please verify the password entered.", 'warning')
        return redirect(url_for('login'))
    login_user(user, remember = remember_me)
    flash('Logged in successfully!', 'success')
    return redirect(request.args.get('next') or url_for('dashboard'))


def logout():
    logout_user()
    return redirect(url_for('index'))


def upgrade():
    token = request.form['stripeToken']

    if not current_user:
        user = User.query.filter_by(email=request.form['stripeEmail']).first()
        login_user(user)

    sub = None
    try:
        if current_user.stripe_id:
            customer = stripe.Customer.retrieve(current_user.stripe_id)
            sub = customer.subscriptions.data[0] if customer.subscriptions.data else None
        else:
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
    except stripe.CardError:
        flash("Sorry. Your card could not be charged. Please contact us.", "error")
        return redirect(url_for('dashboard'))

    current_user.upgraded = True
    DB.session.add(current_user)
    DB.session.commit()

    return redirect(url_for('dashboard'))


@login_required
def downgrade():
    customer = stripe.Customer.retrieve(current_user.stripe_id)
    sub = customer.subscriptions.data[0] if customer.subscriptions.data else None

    if not sub:
        flash("You are not subscribed to any plan", "warning")

    sub = sub.delete(at_period_end=True)
    flash("Your were unregistered from the Formspree Gold plan. Your card will not be charged anymore, but your plan will remain active until %s." % datetime.datetime.fromtimestamp(sub.current_period_end).strftime('%A, %B %d, %Y')) 

    return redirect(url_for('account'))


def stripe_webhook():
    event = request.get_json()
    if event['type'] == 'customer.subscription.deleted':
        customer_id = event['data']['object']['customer']
        customer = stripe.Customer.retrieve(customer_id)
        if len(customer.subscriptions.data) == 0:
            user = User.query.filter_by(stripe_id=customer_id).first()
            user.upgraded = False
            DB.session.add(user)
            DB.session.commit()
    return 'ok'


@login_required
def notify_email_confirmation():
    return render_template('info.html',
      title="Please confirm your email",
      text="We've sent an email confirmation to {email}. "
           "Please go there and click on the confirmation "
           "link before you can use your Formspree account."\
           .format(email=current_user.email))


@login_required
def account():
    emails = {
        'verified': (e.address for e in current_user.emails.order_by(Email.registered_on.desc())),
        'pending': filter(bool, request.cookies.get('pending-emails', '').split(',')),
    }
    return render_template('users/account.html', emails=emails)
