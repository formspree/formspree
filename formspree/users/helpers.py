from flask import render_template, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

from formspree import settings
from formspree.stuff import celery, TEMPLATES
from formspree.utils import send_email


def hash_pwd(password):
    return generate_password_hash(password)


def check_password(hashed, password):
    return check_password_hash(hashed, password)


@celery.task()
def send_downgrade_email(customer_email):
    send_email(
        to=customer_email,
        subject='Successfully downgraded from {} {}'.format(settings.SERVICE_NAME,
                                                            settings.UPGRADED_PLAN_NAME),
        text=render_template('email/downgraded.txt'),
        html=render_template_string(TEMPLATES.get('downgraded.html')),
        sender=settings.DEFAULT_SENDER
    )


@celery.task()
def send_downgrade_reason_email(customer_email, reason):
    send_email(
        to=settings.CONTACT_EMAIL,
        reply_to=customer_email,
        subject='A customer has downgraded from {}'.format(settings.UPGRADED_PLAN_NAME),
        text=render_template('email/downgraded_reason.txt', reason=reason),
        sender=settings.DEFAULT_SENDER
    )
