import stripe
import datetime

from flask import request, jsonify
from flask_login import current_user, login_required

from .models import Email
from .helpers import CARD_MAPPINGS

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

            cards = customer.sources.all(object='card').data
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
