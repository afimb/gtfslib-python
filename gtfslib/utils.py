# -*- coding: utf-8 -*-
#    This file is part of Gtfslib-python.
#
#    Gtfslib-python is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Gtfslib-python is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with gtfslib-python.  If not, see <http://www.gnu.org/licenses/>.
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