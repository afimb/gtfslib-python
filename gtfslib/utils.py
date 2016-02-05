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
from exceptions import ArithmeticError
import bisect
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

class ContinousPiecewiseLinearFunc(object):

    def __init__(self):
        self._x = []
        self._y = []
        self._sorted = True

    def append(self, x, y):
        self._x.append(x)
        self._y.append(y)
        self._sorted = False

    def interpolate(self, x):

        if len(self._x) == 0:
            raise ArithmeticError("Empty piecewise linear function")

        if not self._sorted:
            zipped = zip(self._x, self._y)
            zipped.sort()
            self._x = [ ax for (ax, ay) in zipped ]
            self._y = [ ay for (ax, ay) in zipped ]
            self._sorted = True

        idx = bisect.bisect(self._x, x)
        if idx == 0:
            # Clamp to left
            return self._y[0]
        if idx == len(self._x):
            # Clamp to right
            return self._y[-1]
        x1 = self._x[idx - 1]
        x2 = self._x[idx]
        y1 = self._y[idx - 1]
        y2 = self._y[idx]
        dx = x2 - x1
        # Please note that by construction dx can never be null
        # bisect always return the last item in case several are equals
        dy = y2 - y1
        return (1.0 * x - x1) * dy / dx + y1