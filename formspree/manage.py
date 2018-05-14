import os
import datetime
import click

from flask_script import prompt_bool
from flask_migrate import Migrate

from formspree import app, settings
from formspree.stuff import redis_store, DB
from formspree.forms.helpers import REDIS_COUNTER_KEY
from formspree.forms.models import Form

from celery.bin.celery import main as celery_main

# add flask-migrate commands
migrate = Migrate(app, DB)

@app.cli.command()
def run_debug(port=os.getenv('PORT', 5000)):
    '''runs the app with debug flag set to true'''
    app.run(host='0.0.0.0', debug=True, port=int(port))

@app.cli.command()
@click.option('-i', '--id', default=None, help='form id')
@click.option('-H', '--host', default=None, help='referer hostname')
@click.option('-e', '--email', default=None, help='form email')
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
        print('supply each --email or --form or both (or --id).')
        return 1

    for form in query:
        nsubmissions = redis_store.get(REDIS_COUNTER_KEY(form_id=form.id, month=month)) \
            or 0
        print('%s submissions for %s' % (nsubmissions, form))


@app.cli.command()
@click.option('-t', '--testname', 'testname', default=None, help='name of test')
@click.option('-f', '--failfast', is_flag=True, default=False, help='stop on error')
def test(testname=None, failfast=False):
    import unittest

    test_loader = unittest.defaultTestLoader
    if testname:
        test_suite = test_loader.loadTestsFromName(testname)
    else:
        test_suite = test_loader.discover('.')

    test_runner = unittest.TextTestRunner(failfast=failfast)
    test_runner.run(test_suite)

if __name__ == "__main__":
    app.run()
