from flask.ext.script import Manager, prompt_bool
from flask.ext.migrate import Migrate, MigrateCommand

from formspree import create_app, app

forms_app = create_app()
manager = Manager(forms_app)


# add flask-migrate commands
Migrate(forms_app, app.DB)
manager.add_command('db', MigrateCommand)

@manager.command
def run_debug(port=5000):
    '''runs the app with debug flag set to true'''
    forms_app.run(host='0.0.0.0', debug=True, port=int(port))


@manager.option('-H', '--host', dest='host', default=None, help='referer hostname')
@manager.option('-e', '--email', dest='email', default=None, help='form email')
def unsubscribe(email, host):
    ''' Unsubscribes an email by resetting the form to unconfirmed. User may get
    one more confirmation email, but if she doesn't confirm that will be it.'''

    from formspree.forms.models import Form
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

if __name__ == "__main__":
    manager.run()
