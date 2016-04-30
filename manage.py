import os
import dotenv

# Must come first, even before some imports. It reads the .env file and put the content as environment variables.
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import datetime

from flask.ext.script import Manager, prompt_bool
from flask.ext.migrate import Migrate, MigrateCommand

from formspree import create_app, app
from formspree.app import redis_store
from formspree.forms.helpers import MONTHLY_COUNTER_KEY
from formspree.forms.models import Form

forms_app = create_app()
manager = Manager(forms_app)

# add flask-migrate commands
Migrate(forms_app, app.DB)
manager.add_command('db', MigrateCommand)


@manager.command
def run_debug(port=os.getenv('PORT', 5000)):
    '''runs the app with debug flag set to true'''
    forms_app.run(host='0.0.0.0', debug=True, port=int(port))


@manager.option('-H', '--host', dest='host', default=None, help='referer hostname')
@manager.option('-e', '--email', dest='email', default=None, help='form email')
def unsubscribe(email, host):
    ''' Unsubscribes an email by resetting the form to unconfirmed. User may get
    one more confirmation email, but if she doesn't confirm that will be it.'''

    form = None

    if email and host:
        form = Form.query.filter_by(email=email, host=host).first()
    elif email and not host:
        query = Form.query.filter_by(email=email)
        if query.count() == 1:
            form = query.first()
        elif query.count() > 1:
            for f in query.all():
                print '-', f.host
            print 'More than one result for this email, specify the host.'
    elif host and not email:
        query = Form.query.filter_by(host=host)
        if query.count() == 1:
            form = query.first()
        elif query.count() > 1:
            for f in query.all():
                print '-', f.email
            print 'More than one result for this host, specify the email.'

    if form:
        print 'unsubscribing the email %s from the form at %s' % (form.email, form.host)
        if prompt_bool('are you sure?'):
            form.confirmed = False
            form.confirm_sent = False
            app.DB.session.add(form)
            app.DB.session.commit()
            print 'success.'


@manager.option('-i', '--id', dest='id', default=None, help='form id')
@manager.option('-H', '--host', dest='host', default=None, help='referer hostname')
@manager.option('-e', '--email', dest='email', default=None, help='form email')
def monthly_counters(email=None, host=None, id=None, month=datetime.date.today().month):
    if id:
        query = [Form.query.get(id)]
    elif email and host:
        query = Form.query.filter_by(email=email, host=host)
    elif email and not host:
        query = Form.query.filter_by(email=email)
    elif host and not email:
        query = Form.query.filter_by(host=host)
    else:
        print 'supply each --email or --form or both (or --id).'
        return 1

    for form in query:
        nsubmissions = redis_store.get(MONTHLY_COUNTER_KEY(form_id=form.id, month=month)) or 0
        print '%s submissions for %s' % (nsubmissions, form)


@manager.command
def test():
    import unittest

    test_loader = unittest.defaultTestLoader
    test_suite = test_loader.discover('.')

    test_runner = unittest.TextTestRunner()
    test_runner.run(test_suite)

if __name__ == "__main__":
    manager.run()
