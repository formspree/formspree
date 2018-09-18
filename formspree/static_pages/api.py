from flask import jsonify

from formspree import settings


def config():
    return jsonify({
        'SERVICE_NAME': settings.SERVICE_NAME,
        'SERVICE_URL': settings.SERVICE_URL,
        'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY
    })
