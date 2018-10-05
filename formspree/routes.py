import formspree.forms.views as fv
import formspree.forms.api as fa
import formspree.users.views as uv
import formspree.users.api as ua
import formspree.static_pages.views as sv

def configure_routes(app):
    app.add_url_rule('/', 'index', view_func=sv.default, methods=['GET'])
    app.add_url_rule('/favicon.ico', view_func=sv.favicon)
    app.add_url_rule('/formspree-verify.txt', view_func=sv.formspree_verify)

    # public forms
    app.add_url_rule('/<email_or_string>', 'send', view_func=fv.send, methods=['GET', 'POST'])
    app.add_url_rule('/unblock/<email>', 'unblock_email', view_func=fv.unblock_email, methods=['GET', 'POST'])
    app.add_url_rule('/resend/<email>', 'resend_confirmation', view_func=fv.resend_confirmation, methods=['POST'])
    app.add_url_rule('/confirm/<nonce>', 'confirm_email', view_func=fv.confirm_email, methods=['GET'])
    app.add_url_rule('/unconfirm/<form_id>', 'request_unconfirm_form', view_func=fv.request_unconfirm_form, methods=['GET'])
    app.add_url_rule('/unconfirm/multiple', 'unconfirm_multiple', view_func=fv.unconfirm_multiple, methods=['POST'])
    app.add_url_rule('/unconfirm/<digest>/<form_id>', 'unconfirm_form', view_func=fv.unconfirm_form, methods=['GET', 'POST'])
    app.add_url_rule('/thanks', 'thanks', view_func=fv.thanks, methods=['GET'])

    # dashboard
    app.add_url_rule('/plans', view_func=sv.serve_plans, methods=['GET'])
    app.add_url_rule('/dashboard', 'dashboard', view_func=sv.serve_dashboard, methods=['GET'])
    app.add_url_rule('/forms', view_func=sv.serve_dashboard, methods=['GET'])
    app.add_url_rule('/forms/<hashid>', view_func=sv.serve_dashboard, methods=['GET'])
    app.add_url_rule('/forms/<hashid>/<path:s>', view_func=sv.serve_dashboard, methods=['GET'])
    app.add_url_rule('/account', 'account', view_func=sv.serve_dashboard, methods=['GET'])
    app.add_url_rule('/account/billing', view_func=sv.serve_dashboard, methods=['GET'])

    # login stuff
    app.add_url_rule('/register', 'register', view_func=uv.register, methods=['GET', 'POST'])
    app.add_url_rule('/login', 'login', view_func=uv.login, methods=   ['GET', 'POST'])
    app.add_url_rule('/login/reset', 'forgot-password', view_func=uv.forgot_password, methods=['GET', 'POST'])
    app.add_url_rule('/login/reset/<digest>', 'reset-password', view_func=uv.reset_password, methods=['GET', 'POST'])
    app.add_url_rule('/logout', 'logout', view_func=uv.logout, methods=['GET'])

    # users
    app.add_url_rule('/account/billing/invoice/<invoice_id>', view_func=uv.invoice, methods=['GET'])
    app.add_url_rule('/account/confirm/<digest>', 'confirm-account-email', view_func=uv.confirm_account_email, methods=['GET'])
    app.add_url_rule('/api-int/account', view_func=ua.get_account, methods=['GET'])
    app.add_url_rule('/api-int/account/billing', view_func=ua.update_invoice_address, methods=['PATCH'])
    app.add_url_rule('/api-int/account/add-email', view_func=ua.add_email, methods=['POST'])
    app.add_url_rule('/api-int/buy', view_func=ua.buy, methods=['POST'])
    app.add_url_rule('/api-int/cancel', view_func=ua.cancel, methods=['POST'])
    app.add_url_rule('/api-int/cards', view_func=ua.add_card, methods=['PUT'])
    app.add_url_rule('/api-int/cards/<cardid>/default', view_func=ua.change_default_card, methods=['PUT'])
    app.add_url_rule('/api-int/cards/<cardid>', view_func=ua.delete_card, methods=['DELETE'])

    # users' forms
    app.add_url_rule('/forms/<hashid>.<format>', view_func=fv.export_submissions, methods=['GET'])
    app.add_url_rule('/forms/whitelabel/preview', view_func=fv.custom_template_preview_render, methods=['GET'])
    app.add_url_rule('/api-int/forms', view_func=fa.list, methods=['GET'])
    app.add_url_rule('/api-int/forms', view_func=fa.create, methods=['POST'])
    app.add_url_rule('/api-int/forms/<hashid>', view_func=fa.get, methods=['GET'])
    app.add_url_rule('/api-int/forms/<hashid>', view_func=fa.update, methods=['PATCH'])
    app.add_url_rule('/api-int/forms/<hashid>', view_func=fa.delete, methods=['DELETE'])
    app.add_url_rule('/api-int/forms/sitewide-check', view_func=fa.sitewide_check, methods=['POST'])
    app.add_url_rule('/api-int/forms/<hashid>/submissions/<submissionid>', view_func=fa.submission_delete, methods=['DELETE'])
    app.add_url_rule('/api-int/forms/<hashid>/whitelabel', view_func=fa.custom_template_set, methods=['PUT'])

    # webhooks
    app.add_url_rule('/webhooks/stripe', view_func=uv.stripe_webhook, methods=['POST'])

    # any other static pages and 404
    app.add_url_rule('/<path:template>', 'default', view_func=sv.default, methods=['GET'])
