import forms
import users
import static_pages

def configure_routes(app):
    app.add_url_rule('/', 'index', view_func=static_pages.views.default, methods=['GET'])
    app.add_url_rule('/favicon.ico', view_func=static_pages.views.favicon)
    app.add_url_rule('/formspree-verify.txt', view_func=static_pages.views.formspree_verify)

    # Public forms
    app.add_url_rule('/<email_or_string>', 'send', view_func=forms.views.send, methods=['GET', 'POST'])
    app.add_url_rule('/unblock/<email>', 'unblock_email', view_func=forms.views.unblock_email, methods=['GET', 'POST'])
    app.add_url_rule('/resend/<email>', 'resend_confirmation', view_func=forms.views.resend_confirmation, methods=['POST'])
    app.add_url_rule('/confirm/<nonce>', 'confirm_email', view_func=forms.views.confirm_email, methods=['GET'])
    app.add_url_rule('/unconfirm/<digest>/<form_id>', 'unconfirm_form', view_func=forms.views.unconfirm_form, methods=['POST'])
    app.add_url_rule('/thanks', 'thanks', view_func=forms.views.thanks, methods=['GET'])

    # Users
    app.add_url_rule('/account', 'account', view_func=users.views.account, methods=['GET'])
    app.add_url_rule('/account/upgrade', 'account-upgrade', view_func=users.views.upgrade, methods=['POST'])
    app.add_url_rule('/account/downgrade', view_func=users.views.downgrade, methods=['POST'])
    app.add_url_rule('/account/resubscribe', view_func=users.views.resubscribe, methods=['POST'])
    app.add_url_rule('/card/add', 'add-card', view_func=users.views.add_card, methods=['POST'])
    app.add_url_rule('/card/<cardid>/default', 'change-default-card', view_func=users.views.change_default_card, methods=['POST'])
    app.add_url_rule('/card/<cardid>/delete', 'delete-card', view_func=users.views.delete_card, methods=['POST'])
    app.add_url_rule('/account/billing', 'billing-dashboard', view_func=users.views.billing, methods=['GET'])
    app.add_url_rule('/account/billing/invoice/update-invoice-address', 'update-invoice-address', view_func=users.views.update_invoice_address, methods=['POST'])
    app.add_url_rule('/account/billing/invoice/<invoice_id>', view_func=users.views.invoice, methods=['GET'])
    app.add_url_rule('/account/add-email', 'add-account-email', view_func=users.views.add_email, methods=['POST'])
    app.add_url_rule('/account/confirm/<digest>', 'confirm-account-email', view_func=users.views.confirm_email, methods=['GET'])
    app.add_url_rule('/register', 'register', view_func=users.views.register, methods=['GET', 'POST'])
    app.add_url_rule('/login', 'login', view_func=users.views.login, methods=   ['GET', 'POST'])
    app.add_url_rule('/login/reset', 'forgot-password', view_func=users.views.forgot_password, methods=['GET', 'POST'])
    app.add_url_rule('/login/reset/<digest>', 'reset-password', view_func=users.views.reset_password, methods=['GET', 'POST'])
    app.add_url_rule('/logout', 'logout', view_func=users.views.logout, methods=['GET'])

    # Users' forms
    app.add_url_rule('/dashboard', 'dashboard', view_func=forms.views.forms, methods=['GET'])
    app.add_url_rule('/forms', 'forms', view_func=forms.views.forms, methods=['GET'])
    app.add_url_rule('/forms', 'create-form', view_func=forms.views.create_form, methods=['POST'])
    app.add_url_rule('/forms/sitewide-check', view_func=forms.views.sitewide_check, methods=['GET'])
    app.add_url_rule('/forms/<hashid>/', 'form-submissions', view_func=forms.views.form_submissions, methods=['GET'])
    app.add_url_rule('/forms/<hashid>.<format>', 'form-submissions', view_func=forms.views.form_submissions, methods=['GET'])
    app.add_url_rule('/forms/<hashid>/toggle-recaptcha', 'toggle-recaptcha', view_func=forms.views.form_recaptcha_toggle, methods=['GET'])
    app.add_url_rule('/forms/<hashid>/toggle', 'form-toggle', view_func=forms.views.form_toggle, methods=['POST'])
    app.add_url_rule('/forms/<hashid>/delete', 'form-deletion', view_func=forms.views.form_deletion, methods=['POST'])
    app.add_url_rule('/forms/<hashid>/delete/<submissionid>', 'submission-deletion', view_func=forms.views.submission_deletion, methods=['POST'])

    # Webhooks
    app.add_url_rule('/webhooks/stripe', view_func=users.views.stripe_webhook, methods=['POST'])

    # Any other static pages and 404
    app.add_url_rule('/<path:template>', 'default', view_func=static_pages.views.default, methods=['GET'])
