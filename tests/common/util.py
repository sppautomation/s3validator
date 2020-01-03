
import logging
import os
import tempfile
import traceback
from hurry.filesize import size

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

def get_offload_size(offload_in_bytes):


    return size(offload_in_bytes)
    # if offload > (1000 * 1000 * 1000 * 1000):
    #     size = offload / (1000 * 1000 * 1000 * 1000)
    #     size_value = "TB"
    # elif offload > (1000 * 1000 * 1000):
    #     size = offload / (1000 * 1000 * 1000)
    #     size_value = "GB"
    # elif offload > (1000 * 1000):
    #     size = offload / (1000 * 1000)
    #     size_value = "MB"
    # elif offload > (1000):
    #     size = offload / (1000)
    #     size_value = "KB"
    # else:
    #     size = offload
    #     size_value = "Bytes"

    # return size, size_value


