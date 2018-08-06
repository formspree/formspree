import os
from premailer import transform

TEMPLATES_DIR = 'formspree/templates/email/pre_inline_style/'

def generate_templates():
    template_map = dict()
    for filename in os.listdir(TEMPLATES_DIR):
        if filename.endswith('.html'):
            # print (TEMPLATES_DIR + filename)
            with open(TEMPLATES_DIR + filename, 'r') as html: # TODO: this is a bad way to do this, need to figure this out with os.path
                transformed_template = transform(html.read())

                # weird issue with jinja templates beforehand so we use this hack
                # see https://github.com/peterbe/premailer/issues/72
                mapping = (('%7B%7B%20', '{{ '), ('%20%7D%7D', ' }}'))
                for k, v in mapping:
                    transformed_template = transformed_template.replace(k, v)

                template_map[filename] = transformed_template

    for item in template_map:
        print(item)
    return template_map
