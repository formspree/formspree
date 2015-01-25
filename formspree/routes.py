import forms
import users
import static_pages

def configure_routes(app):
    app.add_url_rule('/', 'index', view_func=static_pages.views.default, methods=['GET'])
    app.add_url_rule('/favicon.ico', view_func=static_pages.views.favicon)
    app.add_url_rule('/<path:template>', 'default', view_func=static_pages.views.default, methods=['GET'])

    # Forms
    app.add_url_rule('/<email_or_string>', 'send', view_func=forms.views.send, methods=['GET', 'POST'])
    app.add_url_rule('/confirm/<nonce>', 'confirm_email', view_func=forms.views.confirm_email, methods=['GET'])
    app.add_url_rule('/thanks', 'thanks', view_func=forms.views.thanks, methods=['GET'])

    # Users
    app.add_url_rule('/dashboard', 'dashboard', view_func=users.views.dashboard, methods=['GET'])
    app.add_url_rule('/register', 'register', view_func=users.views.register, methods=['GET', 'POST'])
    app.add_url_rule('/login', 'login', view_func=users.views.login, methods=   ['GET', 'POST'])
    app.add_url_rule('/logout', 'logout', view_func=users.views.logout, methods=['GET'])

    app.add_url_rule('/forms', 'forms-api', view_func=forms.views.forms, methods=['GET', 'POST'])
