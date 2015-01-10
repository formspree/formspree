import forms

def configure_routes(app):
    app.add_url_rule('/', 'index', view_func=forms.views.default, methods=['GET'])
    app.add_url_rule('/favicon.ico', view_func=forms.views.favicon)
    app.add_url_rule('/<email>', 'send', view_func=forms.views.send, methods=['GET', 'POST'])
    app.add_url_rule('/confirm/<nonce>', 'confirm_email', view_func=forms.views.confirm_email, methods=['GET'])
    app.add_url_rule('/thanks', 'thanks', view_func=forms.views.thanks, methods=['GET'])
    app.add_url_rule('/<path:template>', 'default', view_func=forms.views.default, methods=['GET'])
