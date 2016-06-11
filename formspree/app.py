import json
import stripe

import flask
from flask import g
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, current_user
from flask.ext.cdn import CDN
from flask_redis import Redis
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import settings
from helpers import ssl_redirect

DB = SQLAlchemy()
redis_store = Redis()
stripe.api_key = settings.STRIPE_SECRET_KEY
cdn = CDN()

import routes
from users.models import User

def configure_login(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'register'

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    @app.before_request
    def before_request():
        g.user = current_user


def create_app():
    app = flask.Flask(__name__)
    app.config.from_object(settings)

    DB.init_app(app)
    redis_store.init_app(app)
    routes.configure_routes(app)
    configure_login(app)

    app.jinja_env.filters['json'] = json.dumps
    app.config['CDN_DOMAIN'] = settings.CDN_URL
    app.config['CDN_HTTPS'] = True
    cdn.init_app(app)

    Limiter(
        app,
        key_func=get_remote_address,
        global_limits=['30 per hour'],
        storage_uri=settings.REDIS_URL
    )

    if not app.debug and not app.testing:
        ssl_redirect(app)
    return app
