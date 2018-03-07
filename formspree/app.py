import json
import stripe
import structlog

from flask import Flask, g, request, redirect
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, current_user
from flask.ext.cdn import CDN
from flask_redis import Redis
from flask_limiter import Limiter
from flask_limiter.util import get_ipaddr
import settings

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


def configure_ssl_redirect(app):
    @app.before_request
    def get_redirect():
        if not request.is_secure and \
           not request.headers.get('X-Forwarded-Proto', 'http') == 'https' and \
           request.method == 'GET' and request.url.startswith('http://'):
            url = request.url.replace('http://', 'https://', 1)
            r = redirect(url, code=301)
            return r


def configure_logger(app):
    def processor(_, method, event):
        # we're on heroku, so we can count that heroku will
        # timestamp the logs.
        levelcolor = {
            'debug': 32,
            'info': 34,
            'warning': 33,
            'error': 31
        }.get(method, 37)

        msg = event.pop('event')

        rest = []
        for k, v in event.items():
            if type(v) is unicode:
                v = v.encode('utf-8', 'ignore')
            rest.append('\x1b[{}m{}\x1b[0m={}'.format(
                levelcolor,
                k.upper(),
                v
            ))
        rest = ' '.join(rest)

        return '\x1b[{clr}m{met}\x1b[0m [\x1b[35m{rid}\x1b[0m] {msg} {rest}'. \
            format(
                clr=levelcolor,
                met=method.upper(),
                rid=request.headers.get('X-Request-Id', '~')[-7:],
                msg=msg,
                rest=rest
            )

    structlog.configure(
        processors=[
            structlog.processors.ExceptionPrettyPrinter(),
            processor
        ]
    )

    logger = structlog.get_logger()

    @app.before_request
    def get_request_id():
        g.log = logger.new()


def create_app():
    app = Flask(__name__)
    app.config.from_object(settings)

    DB.init_app(app)
    redis_store.init_app(app)
    routes.configure_routes(app)
    configure_login(app)
    configure_logger(app)

    app.jinja_env.filters['json'] = json.dumps

    def epoch_to_date(s):
        import datetime
        return datetime.datetime.fromtimestamp(s).strftime('%B %-d, %Y')

    def epoch_to_ts(s):
        import datetime
        return datetime.datetime.fromtimestamp(s).strftime('%m-%-d-%Y %H:%M')

    app.jinja_env.filters['epoch_to_date'] = epoch_to_date
    app.jinja_env.filters['epoch_to_ts'] = epoch_to_ts
    app.config['CDN_DOMAIN'] = settings.CDN_URL
    app.config['CDN_HTTPS'] = True
    cdn.init_app(app)

    if not app.debug and not app.testing:
        configure_ssl_redirect(app)

    Limiter(
        app,
        key_func=get_ipaddr,
        global_limits=[settings.RATE_LIMIT],
        storage_uri=settings.REDIS_RATE_LIMIT
    )

    return app
