from . import settings
from .create_app import create_app

app = create_app()

def debuggable_app():
    """ For launching with gunicorn from a Heroku Procfile. 
    Problem: both the web and worker processes run the same create_app code. If we start a ptvsd service in create_app, it will be
    started twice on the same port, and fail. 
    Solution: gunicorn gets its app object through this method that also starts the debug server. 
    """
    if settings.DEBUG:
        import ptvsd
        ptvsd.enable_attach(address=('0.0.0.0', 3000))

    return app

from . import manage
