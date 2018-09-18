from flask import request, render_template, g, \
                  redirect, url_for
from jinja2 import TemplateNotFound
from flask_login import login_required


@login_required
def serve_dashboard(hashid=None, s=None):
    return render_template('static_pages/dashboard.html')


def default(template='index'):
    template = template if template.endswith('.html') else template+'.html'
    try:
        return render_template('static_pages/' + template,
                               is_redirect=request.args.get('redirected'))
    except TemplateNotFound:
        return render_template('static_pages/404.html'), 404


def internal_error(e):
    import traceback
    g.log.error(traceback.format_exc())
    return render_template('static_pages/500.html'), 500


def favicon():
    return redirect(url_for('static', filename='img/favicon.ico'))


def formspree_verify():
    return redirect(url_for('static', filename='formspree-verify.txt'))
