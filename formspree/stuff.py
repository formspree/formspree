import stripe
from flask_sqlalchemy import SQLAlchemy
from flask_cdn import CDN
from flask_redis import Redis
from celery import Celery

from .template import generate_templates
from . import settings

DB = SQLAlchemy()
redis_store = Redis()
stripe.api_key = settings.STRIPE_SECRET_KEY
cdn = CDN()
celery = Celery(__name__, broker=settings.CELERY_BROKER_URL)
TEMPLATES = generate_templates()
