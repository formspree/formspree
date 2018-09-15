web: gunicorn 'formspree:debuggable_app()'
worker: celery worker --app=formspree.stuff
release: flask db upgrade
