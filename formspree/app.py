import flask
from flask import g
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, current_user
import fakeredis, redis
import settings

DB = SQLAlchemy()
if settings.TESTING:
    REDIS = fakeredis.FakeStrictRedis()
else:
    REDIS = redis.StrictRedis.from_url(settings.REDIS_URL)

import routes
from users.models import User

def configure_login(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(id):
        print "hey"
        return User.query.get(int(id))

    @app.before_request
    def before_request():
        g.user = current_user

def create_app():
    app = flask.Flask(__name__)
    app.config.from_object(settings)

    DB.init_app(app)
    routes.configure_routes(app)
    configure_login(app)

    app.jinja_env.filters['nl2br'] = lambda value: value.replace('\n','<br>\n')

    return app
