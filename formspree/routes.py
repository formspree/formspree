import forms
import users
import static_pages

def configure_routes(app):
    app.add_url_rule('/', 'index', view_func=static_pages.views.default, methods=['GET'])
    app.add_url_rule('/favicon.ico', view_func=static_pages.views.favicon)
    app.add_url_rule('/<path:template>', 'default', view_func=static_pages.views.default, methods=['GET'])

    # Public forms
    app.add_url_rule('/<email_or_string>', 'send', view_func=forms.views.send, methods=['GET', 'POST'])
    app.add_url_rule('/confirm/<nonce>', 'confirm_email', view_func=forms.views.confirm_email, methods=['GET'])
    app.add_url_rule('/thanks', 'thanks', view_func=forms.views.thanks, methods=['GET'])

    # Users
    app.add_url_rule('/account', 'account', view_func=users.views.account, methods=['GET'])
    app.add_url_rule('/account/upgrade', view_func=users.views.upgrade, methods=['POST'])
    app.add_url_rule('/account/downgrade', view_func=users.views.downgrade, methods=['POST'])
    app.add_url_rule('/account/add-email', view_func=users.views.add_email, methods=['POST'])
    app.add_url_rule('/account/confirm/<digest>', 'confirm_account_email', view_func=users.views.confirm_email, methods=['GET'])
    app.add_url_rule('/account/confirm', 'notify_email_confirmation', view_func=users.views.notify_email_confirmation, methods=['GET'])
    app.add_url_rule('/register', 'register', view_func=users.views.register, methods=['GET', 'POST'])
    app.add_url_rule('/login', 'login', view_func=users.views.login, methods=   ['GET', 'POST'])
    app.add_url_rule('/logout', 'logout', view_func=users.views.logout, methods=['GET'])

    # Users' forms
    app.add_url_rule('/dashboard', 'dashboard', view_func=forms.views.forms, methods=['GET'])
    app.add_url_rule('/forms', 'forms', view_func=forms.views.forms, methods=['GET', 'POST'])
    app.add_url_rule('/forms/<random_like_string>/', 'form-submissions', view_func=forms.views.form_submissions, methods=['GET'])

    # Webhooks
    app.add_url_rule('/webhooks/stripe', view_func=users.views.stripe_webhook, methods=['POST'])
