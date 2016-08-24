from flask import request, render_template, redirect, url_for

def default(template='index'):
    template = template if template.endswith('.html') else template+'.html'
    return render_template("static_pages/"+template, is_redirect = request.args.get('redirected'))

def internal_error(e):
    import traceback
    log.error(traceback.format_exc())
    return render_template('static_pages/500.html'), 500

def page_not_found(e):
    return render_template('error.html', title='Oops, page not found'), 404

def favicon():
    return redirect(url_for('static', filename='img/favicon.ico'))

def formspree_verify():
    return redirect(url_for('static', filename='formspree-verify.txt'))
