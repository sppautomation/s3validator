
import logging
import os
import tempfile
import traceback

def get_temp_filename(prefix, suffix='.txt', dir=None, remove=False):
    fd, fname = tempfile.mkstemp(suffix, prefix, dir=dir)
    os.close(fd)

    if remove:
        os.remove(fname)

    return fname

def run_silently(func):
    try:
        func()
    except:
        logging.error(traceback.format_exc())

def run_silently_pred(predicate, func):
    try:
        if predicate:
            func()
    except:
        logging.error(traceback.format_exc())
