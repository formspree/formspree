import os
from flask import render_template
from premailer import transform

TEMPLATES_DIR = 'formspree/templates/email/pre_inline_style/'

def generate_templates():
    template_map = dict()
    for filename in os.listdir(TEMPLATES_DIR):
        if filename.endswith('.html'):
            # print (TEMPLATES_DIR + filename)
            with open(TEMPLATES_DIR + filename, 'r') as html: # TODO: this is a bad way to do this, need to figure this out with os.path
                data = html.read()
                template_map[filename] = transform(data)


    return template_map
