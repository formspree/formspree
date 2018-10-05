import stripe
import datetime

from flask import request, jsonify, g
from flask_login import current_user, login_required, login_user

from formspree.stuff import DB
from .models import Email, User
from .helpers import CARD_MAPPINGS, send_downgrade_reason_email


@login_required
def get_account():
    emails = {
        'verified': [e.address for e in current_user.emails.order_by(Email.registered_on.desc())],
        'pending': [addr for addr in request.cookies.get('pending-emails', '').split(',') if addr],
    }
    sub = None
    cards = {}
    invoices = []

    if current_user.stripe_id:
        try:
            customer = stripe.Customer.retrieve(current_user.stripe_id)

            sub = customer.subscriptions.data[0] if customer.subscriptions.data \
                    else None
            invoices = stripe.Invoice.list(customer=customer, limit=12)

            cards = customer.sources.list(object='card').data
            for card in cards:
                if customer.default_source == card.id:
                    card.default = True
                card.css_name = CARD_MAPPINGS[card.brand]

        except stripe.error.StripeError:
            return jsonify({
                ok: False,
                error: "Failed to get your subscription details from Stripe."
            }), 503

    return jsonify({
        'ok': True,
        'user': current_user.serialize(),
        'emails': emails,
        'cards': cards,
        'invoices': [{
            'id': inv.id,
            'date':  datetime.datetime.fromtimestamp(inv.date).strftime('%A, %B %d, %Y'),
            'attempted': inv.attempted,
            'total': inv.total,
            'paid': inv.paid
        } for inv in invoices],
        'sub': {
            'cancel_at_period_end': sub.cancel_at_period_end,
            'current_period_end': datetime.datetime.fromtimestamp(sub.current_period_end).strftime('%A, %B %d, %Y'),
        } if sub else None
    })


@login_required
def add_email():
    address = request.get_json().get('address').lower().strip()
    g.log = g.log.bind(address=address, account=current_user.email)

    if Email.query.get([address, current_user.id]):
        g.log.info('Failed to add email to account. Already registered.')
        return jsonify({'ok': True}), 200
    try:
        g.log.info('Adding new email address to account.')
        sent = Email.send_confirmation(address, current_user.id)
        if sent:
            pending = request.cookies.get('pending-emails', '').split(',')
            pending.append(address)

            res = jsonify({'ok': True})
            res.set_cookie('pending-emails', ','.join(pending), max_age=10800)
            return res, 202
        else:
            return jsonify({
                'ok': False,
                'error': "We couldn't sent you the verification email at {}. "
                         "Please try again later.".format(address)
            }), 500
    except ValueError:
        return jsonify({
            'ok': False,
            'error': '{} is not a valid email address.'.format(address)
        }), 400


def buy():
    data = request.get_json()

    if 'email' in data:
        try:
            user = User.register(data['email'], data['password'])
            g.log.info('User created.', ip=request.headers.get('X-Forwarded-For'))
        except ValueError:
            return jsonify({'ok': False, 'error': 'Invalid email address.'}), 400
        login_user(user, remember=True)

    # from now on we have current_user for sure
    g.log = g.log.bind(account=current_user.email)

    token = data['token']
    plan = data['plan']

    g.log.info('Upgrading account.', plan=plan)

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
                source=token,
                metadata={'formspree_id': current_user.id}
            )
            current_user.stripe_id = customer.id

        if sub:
            sub.plan = plan
            sub.save()
        else:
            customer.subscriptions.create( plan=plan)
    except stripe.CardError as e:
        g.log.warning("Couldn't charge card.", reason=e.json_body,
                      status=e.http_status)
        return jsonify({'ok': False, 'error': "Couldn't charge card."}), 403

    current_user.plan = plan
    DB.session.add(current_user)
    DB.session.commit()
    g.log.info('Subscription created.')

    return jsonify({'ok': True})


@login_required
def cancel():
    data = request.get_json()

    customer = stripe.Customer.retrieve(current_user.stripe_id)
    sub = customer.subscriptions.data[0] if customer.subscriptions.data else None

    if not sub:
        return jsonify({
            'ok': False,
            'error': "You can't do this. You are not subscribed to any plan."
        }), 403

    reason = data.get('why')
    if reason:
        send_downgrade_reason_email.delay(current_user.email, reason)

    sub.cancel_at_period_end = True
    sub.save()

    g.log.info('Subscription canceled from dashboard.', account=current_user.email)

    at = datetime.datetime.fromtimestamp(sub.current_period_end).strftime('%A, %B %d, %Y')
    return jsonify({'ok': True, 'at': at})


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

        # make sure this card doesn't already exist
        new_fingerprint = stripe.Token.retrieve(token).card.fingerprint
        if new_fingerprint in (card.fingerprint for card in customer.sources.list(object='card').data):
            return jsonify({'ok': True}), 200
        else:
            customer.sources.create(source=token)
            g.log.info('Added card to stripe account.')
            return jsonify({'ok': True}), 201

    except stripe.CardError as e:
        g.log.warning("Couldn't add card to Stripe account.",
                      reason=e.json_body, status=e.http_status)
        return jsonify({
            'ok': False,
            'error': "Sorry, there was an error in adding your card. If this persists, please contact us."
        }), 400
    except stripe.error.APIConnectionError:
        g.log.warning("Couldn't add card to Stripe account. Failed to "
                      "communicate with Stripe API.")
        return jsonify({
            'ok': False,
            'error': "We're unable to establish a connection with our payment "
              "processor. For your security, we haven't added this "
              "card to your account. Please try again later."
        }), 503
    except stripe.error.StripeError:
        g.log.warning("Couldn't add card to Stripe account. Unknown error.")
        return jsonify({
            'ok': False,
            'error': 'Sorry, an unknown error occured. Please try again '
              'later. If this problem persists, please contact us.'
        }), 503

    return redirect(url_for('billing-dashboard'))

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
    return redirect(url_for('billing-dashboard'))

@login_required
def delete_card(cardid):
    if current_user.stripe_id:
        customer = stripe.Customer.retrieve(current_user.stripe_id)
        customer.sources.retrieve(cardid).delete()
        flash(u'Successfully deleted card', 'success')
        g.log.info('Deleted card from account.', account=current_user.email)
    else:
        flash(u"That's an invalid operation", 'error')
    return redirect(url_for('billing-dashboard'))


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
