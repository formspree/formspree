import sys
import traceback
from flask import request, render_template, g, \
                  redirect, url_for
from jinja2 import TemplateNotFound


def default(template='index'):
    template = template if template.endswith('.html') else template+'.html'
    try:
        return render_template('static_pages/' + template,
                               is_redirect=request.args.get('redirected'))
    except TemplateNotFound:
        return render_template('static_pages/404.html'), 404


def internal_error(e):
    g.log.error(e)
    exc = traceback.format_exception(sys.exc_type, sys.exc_value,
                                     sys.exc_traceback)
    return render_template('static_pages/500.html',
                           exception=''.join(exc)), 500


def favicon():
    return redirect(url_for('static', filename='img/favicon.ico'))


def formspree_verify():
    return redirect(url_for('static', filename='formspree-verify.txt'))
