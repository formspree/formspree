import settings
import re
import hashlib

HASH = lambda x, y: hashlib.md5(x+y+settings.NONCE_SECRET).hexdigest()
IS_VALID_EMAIL = lambda x: re.match(r"[^@]+@[^@]+\.[^@]+", x)
EXCLUDE_KEYS = ['_gotcha', '_next', '_subject', '_cc']
