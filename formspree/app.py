import flask
from flask.ext.sqlalchemy import SQLAlchemy
import settings

DB = SQLAlchemy()

import routes
def create_app():
    app = flask.Flask(__name__)
    app.config.from_object(settings)

    DB.init_app(app)
    routes.configure_routes(app)

    app.jinja_env.filters['nl2br'] = lambda value: value.replace('\n','<br>\n')

    return app
