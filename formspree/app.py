import stripe

import flask
from flask import g
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, current_user
from flask_redis import Redis
import settings

DB = SQLAlchemy()
redis_store = Redis()
stripe.api_key = settings.STRIPE_SECRET_KEY

import routes
from users.models import User

def configure_login(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

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

    app.jinja_env.filters['nl2br'] = lambda value: value.replace('\n','<br>\n')

    return app
