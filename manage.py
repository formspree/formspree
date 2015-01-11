
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

from formspree import create_app, app

forms_app = create_app()
manager = Manager(forms_app)


# add flask-migrate commands
Migrate(forms_app, app.DB)
manager.add_command('db', MigrateCommand)

@manager.command
def run(port=5000):
    app.run(port=int(port))


if __name__ == "__main__":
    manager.run()
