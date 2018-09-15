from . import settings
from .create_app import create_app

app = create_app()

def debuggable_app():
    if settings.DEBUG:
        import ptvsd
        ptvsd.enable_attach(address=('0.0.0.0', 3000))

    return app

from . import manage
