import os
from premailer import Premailer

TEMPLATES_DIR = 'formspree/templates/email/pre_inline_style/'

def generate_templates():
    template_map = dict()
    for filename in os.listdir(TEMPLATES_DIR):
        if filename.endswith('.html'):
            with open(os.path.join(TEMPLATES_DIR, filename), 'r') as html:
                p = Premailer(html.read(), remove_classes=True)
                transformed_template = p.transform()

                # weird issue with jinja templates beforehand so we use this hack
                # see https://github.com/peterbe/premailer/issues/72
                mapping = (('%7B%7B', '{{'), ('%7D%7D', '}}'), ('%20', ' '))
                for k, v in mapping:
                    transformed_template = transformed_template.replace(k, v)

                template_map[filename] = transformed_template
    return template_map
