import formspree.forms.views as fv
import formspree.forms.api as fa
import formspree.users.views as uv
import formspree.static_pages.views as sv

def configure_routes(app):
    app.add_url_rule('/', 'index', view_func=sv.default, methods=['GET'])
    app.add_url_rule('/favicon.ico', view_func=sv.favicon)
    app.add_url_rule('/formspree-verify.txt', view_func=sv.formspree_verify)

    # Public forms
    app.add_url_rule('/<email_or_string>', 'send', view_func=fv.send, methods=['GET', 'POST'])
    app.add_url_rule('/unblock/<email>', 'unblock_email', view_func=fv.unblock_email, methods=['GET', 'POST'])
    app.add_url_rule('/resend/<email>', 'resend_confirmation', view_func=fv.resend_confirmation, methods=['POST'])
    app.add_url_rule('/confirm/<nonce>', 'confirm_email', view_func=fv.confirm_email, methods=['GET'])
    app.add_url_rule('/unconfirm/<form_id>', 'request_unconfirm_form', view_func=fv.request_unconfirm_form, methods=['GET'])
    app.add_url_rule('/unconfirm/multiple', 'unconfirm_multiple', view_func=fv.unconfirm_multiple, methods=['POST'])
    app.add_url_rule('/unconfirm/<digest>/<form_id>', 'unconfirm_form', view_func=fv.unconfirm_form, methods=['GET', 'POST'])
    app.add_url_rule('/thanks', 'thanks', view_func=fv.thanks, methods=['GET'])

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
    app.add_url_rule('/dashboard', 'dashboard', view_func=fv.serve_dashboard, methods=['GET'])
    app.add_url_rule('/forms', 'dashboard', view_func=fv.serve_dashboard, methods=['GET'])
    app.add_url_rule('/forms/<hashid>', view_func=fv.serve_dashboard, methods=['GET'])
    app.add_url_rule('/forms/<hashid>/<path:s>', view_func=fv.serve_dashboard, methods=['GET'])
    app.add_url_rule('/forms/<hashid>.<format>', view_func=fv.export_submissions, methods=['GET'])
    app.add_url_rule('/api-int/forms', view_func=fa.list, methods=['GET'])
    app.add_url_rule('/api-int/forms', view_func=fa.create, methods=['POST'])
    app.add_url_rule('/api-int/forms/<hashid>', view_func=fa.get, methods=['GET'])
    app.add_url_rule('/api-int/forms/<hashid>', view_func=fa.update, methods=['PATCH'])
    app.add_url_rule('/api-int/forms/<hashid>', view_func=fa.delete, methods=['DELETE'])
    app.add_url_rule('/api-int/forms/sitewide-check', view_func=fa.sitewide_check, methods=['POST'])
    app.add_url_rule('/api-int/forms/<hashid>/submissions/<submissionid>', view_func=fa.submission_delete, methods=['DELETE'])
    app.add_url_rule('/api-int/forms/whitelabel/preview', view_func=fa.custom_template_preview_render, methods=['POST'])

    # Webhooks
    app.add_url_rule('/webhooks/stripe', view_func=uv.stripe_webhook, methods=['POST'])

    # Any other static pages and 404
    app.add_url_rule('/<path:template>', 'default', view_func=sv.default, methods=['GET'])
