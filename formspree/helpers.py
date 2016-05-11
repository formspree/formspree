from flask import request, redirect

def ssl_redirect(app):
    app.before_request(get_redirect)
    app.after_request(set_headers)
    
def get_redirect():
    if not request.is_secure and not request.headers.get('X-Forwarded-Proto', 'http') == 'https' and request.method == 'GET' and request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        r = redirect(url, code=301)
        return r

def set_headers(response):
    if request.is_secure:
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000')
    return response