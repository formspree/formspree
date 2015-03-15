import stripe
import datetime

from flask import request, flash, url_for, render_template, redirect, abort
from flask.ext.login import login_user, logout_user, current_user, login_required
from sqlalchemy.exc import IntegrityError
from helpers import check_password
from formspree.app import DB
from formspree import settings
from models import User

def register():
    if request.method == 'GET':
        return render_template('users/register.html')
    try:
        user = User(request.form['email'], request.form['password'])
        DB.session.add(user)
        DB.session.commit()

    except IntegrityError:
        DB.session.rollback()
        flash("An account with this email already exists.", "error")
        return render_template('users/register.html')

    login_user(user)
    # flash('Your account is successfully registered.') # this is ugly.

    return redirect(url_for('dashboard'))

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
        flash("We can't find an account related with this Email id. Please verify the Email entered.", "error")
        return redirect(url_for('login'))
    elif not check_password(user.password, password):
        flash("Invalid Password. Please verify the password entered.")
        return redirect(url_for('login'))
    login_user(user, remember = remember_me)
    # flash('Logged in successfully') # this is ugly
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
        flash("Your card could not be charged", "error")
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
        flash("You are not subscribed to any plan", "error")

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
def account():
    return render_template('users/account.html')


@login_required
def dashboard():
    if not current_user.upgraded:
        return redirect(url_for('account'))
    return render_template('forms/list.html')

