import formspree.forms.views as fv
import formspree.users.views as uv
import formspree.static_pages.views as sv

def configure_routes(app):
    app.add_url_rule('/', 'index', view_func=sv.default, methods=['GET'])
    app.add_url_rule('/favicon.ico', view_func=sv.favicon)
    app.add_url_rule('/formspree-verify.txt', view_func=sv.formspree_verify)

    # Public forms
# <<<<<<< HEAD
#     app.add_url_rule('/<email_or_string>', 'send', view_func=forms.views.send, methods=['GET', 'POST'])
#     app.add_url_rule('/unblock/<email>', 'unblock_email', view_func=forms.views.unblock_email, methods=['GET', 'POST'])
#     app.add_url_rule('/resend/<email>', 'resend_confirmation', view_func=forms.views.resend_confirmation, methods=['POST'])
#     app.add_url_rule('/confirm/<nonce>', 'confirm_email', view_func=forms.views.confirm_email, methods=['GET'])
#     app.add_url_rule('/unconfirm/<nonce>', 'unconfirm_form', view_func=forms.views.unconfirm_form, methods=['GET'])
#     app.add_url_rule('/thanks', 'thanks', view_func=forms.views.thanks, methods=['GET'])
# =======
    app.add_url_rule('/<email_or_string>', 'send', view_func=fv.send, methods=['GET', 'POST'])
    app.add_url_rule('/unblock/<email>', 'unblock_email', view_func=fv.unblock_email, methods=['GET', 'POST'])
    app.add_url_rule('/resend/<email>', 'resend_confirmation', view_func=fv.resend_confirmation, methods=['POST'])
    app.add_url_rule('/confirm/<nonce>', 'confirm_email', view_func=fv.confirm_email, methods=['GET'])
    app.add_url_rule('/request_unconfirm', 'request_unconfirm', view_func=fv.request_unconfirm, methods=['GET', 'POST'])
    app.add_url_rule('/unconfirm/<digest>/<form_id>', 'unconfirm_form', view_func=fv.unconfirm_form, methods=['POST'])
    app.add_url_rule('/thanks', 'thanks', view_func=fv.thanks, methods=['GET'])
# >>>>>>> master

    # Users
    app.add_url_rule('/account', 'account', view_func=uv.account, methods=['GET'])
    app.add_url_rule('/account/upgrade', 'account-upgrade', view_func=uv.upgrade, methods=['POST'])
    app.add_url_rule('/account/downgrade', view_func=uv.downgrade, methods=['POST'])
    app.add_url_rule('/account/resubscribe', view_func=uv.resubscribe, methods=['POST'])
    app.add_url_rule('/card/add', 'add-card', view_func=uv.add_card, methods=['POST'])
    app.add_url_rule('/card/<cardid>/default', 'change-default-card', view_func=uv.change_default_card, methods=['POST'])
    app.add_url_rule('/card/<cardid>/delete', 'delete-card', view_func=uv.delete_card, methods=['POST'])
    app.add_url_rule('/account/billing', 'billing-dashboard', view_func=uv.billing, methods=['GET'])
    app.add_url_rule('/account/billing/invoice/update-invoice-address', 'update-invoice-address', view_func=uv.update_invoice_address, methods=['POST'])
    app.add_url_rule('/account/billing/invoice/<invoice_id>', view_func=uv.invoice, methods=['GET'])
    app.add_url_rule('/account/add-email', 'add-account-email', view_func=uv.add_email, methods=['POST'])
    app.add_url_rule('/account/confirm/<digest>', 'confirm-account-email', view_func=uv.confirm_email, methods=['GET'])
    app.add_url_rule('/register', 'register', view_func=uv.register, methods=['GET', 'POST'])
    app.add_url_rule('/login', 'login', view_func=uv.login, methods=   ['GET', 'POST'])
    app.add_url_rule('/login/reset', 'forgot-password', view_func=uv.forgot_password, methods=['GET', 'POST'])
    app.add_url_rule('/login/reset/<digest>', 'reset-password', view_func=uv.reset_password, methods=['GET', 'POST'])
    app.add_url_rule('/logout', 'logout', view_func=uv.logout, methods=['GET'])

    # Users' forms
    app.add_url_rule('/dashboard', 'dashboard', view_func=fv.forms, methods=['GET'])
    app.add_url_rule('/forms', 'forms', view_func=fv.forms, methods=['GET'])
    app.add_url_rule('/forms', 'create-form', view_func=fv.create_form, methods=['POST'])
    app.add_url_rule('/forms/sitewide-check', view_func=fv.sitewide_check, methods=['GET'])
    app.add_url_rule('/forms/<hashid>/', 'form-submissions', view_func=fv.form_submissions, methods=['GET'])
    app.add_url_rule('/forms/<hashid>.<format>', 'form-submissions', view_func=fv.form_submissions, methods=['GET'])
    app.add_url_rule('/forms/<hashid>/toggle-recaptcha', 'toggle-recaptcha', view_func=fv.form_recaptcha_toggle, methods=['POST'])
    app.add_url_rule('/forms/<hashid>/toggle-emails', 'toggle-emails', view_func=fv.form_email_notification_toggle, methods=['POST'])
    app.add_url_rule('/forms/<hashid>/toggle-storage', 'toggle-storage', view_func=fv.form_archive_toggle, methods=['POST'])
    app.add_url_rule('/forms/<hashid>/toggle', 'form-toggle', view_func=fv.form_toggle, methods=['POST'])
    app.add_url_rule('/forms/<hashid>/delete', 'form-deletion', view_func=fv.form_deletion, methods=['POST'])
    app.add_url_rule('/forms/<hashid>/delete/<submissionid>', 'submission-deletion', view_func=fv.submission_deletion, methods=['POST'])

    # Webhooks
    app.add_url_rule('/webhooks/stripe', view_func=uv.stripe_webhook, methods=['POST'])

    # Any other static pages and 404
    app.add_url_rule('/<path:template>', 'default', view_func=sv.default, methods=['GET'])
