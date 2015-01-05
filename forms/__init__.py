# -*- coding: utf-8 -*-

from app import create_app
forms_app = create_app()

if __name__ == '__main__':
    forms_app.run(host='0.0.0.0')
