import sys
import os
import datetime

import settings

_LEVEL_MAP = {
    'debug': 4,
    'info': 3,
    'warning': 2,
    'error': 1
}

def _header(level):
    return settings.SERVICE_NAME+":"+level+' '+datetime.datetime.now().isoformat()+" |"

def _handler_stats(handler):
    stats = handler.request.method+" "+\
            handler.request.path+\
            " |"
    return stats

def _should_display(msg_level):
    env_level = getattr(settings, 'LOG_LEVEL', 'debug')
    return _LEVEL_MAP[msg_level.lower()] <= _LEVEL_MAP[env_level]

def _display_msg(msg, level, handler=None):
    if not _should_display(level): return
    if handler: msg = _handler_stats(handler)+msg
    msg = _header(level.upper())+msg
    print msg
    sys.stdout.flush()

def error(msg, handler=None):
    if handler: msg = _handler_stats(handler)+msg
    msg = _header("ERROR")+msg
    print >> sys.stderr, msg

def warning(msg, handler=None):
    _display_msg(msg, 'warning', handler)

def info(msg, handler=None):
    _display_msg(msg, 'info', handler)

def debug(msg, handler=None):
    _display_msg(msg, 'debug', handler)
