import re
from urllib import unquote

def parse_confirmation_link_sent(request_body):
    request_body = unquote(request_body)
    matchlink = re.search('Link:\+([^?]+)\?(\S+)', request_body)
    if not matchlink:
        raise ValueError('No link found in email body:', request_body)

    link = matchlink.group(1)
    qs = matchlink.group(2)

    return link, qs
