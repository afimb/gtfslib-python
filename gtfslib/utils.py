#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Laurent GRÉGOIRE <laurent.gregoire@mecatran.com>
"""
import logging
import time


def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        logging.info("%s() took %0.3f sec" % (f.__name__, time2 - time1))
        return ret
    return wrap

def gtfstime(h, m, s=0):
    return h * 3600 + m * 60 + s

def fmttime(ssm):
    h = ssm / 3600
    ssm %= 3600
    m = ssm / 60
    ssm %= 60
    s = ssm
    return "%d:%02d:%02d" % (h, m, s)