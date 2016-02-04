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
from gtfslib.spatial import orthodromic_distance, orthodromic_seg_distance
import math
"""
@author: Laurent GRÉGOIRE <laurent.gregoire@mecatran.com>
"""

import unittest

class SimplePoint(object):
    def __init__(self, lat, lon):
        self._lat = lat
        self._lon = lon
    def lat(self):
        return self._lat
    def lon(self):
        return self._lon
    def __repr__(self):
        return "<%s(%.6f,%.6f)>" % (self.__class__.__name__, self._lat, self._lon)

class TestSpatial(unittest.TestCase):

    _NAUTICAL_MILE = 1853.248

    def setUp(self):
        pass

    def test_distance(self):
        a = SimplePoint(0, 0)
        b = SimplePoint(1, 0)
        c = SimplePoint(0, 1)
        self.assertAlmostEqual(orthodromic_distance(a, a), 0.0, 3)
        dab = orthodromic_distance(a, b)
        dac = orthodromic_distance(a, c)
        dbc = orthodromic_distance(b, c)
        self.assertAlmostEqual(dab, dac, 3)
        # This is the definition of the nautical mile
        self.assertAlmostEqual(dab / 60, self._NAUTICAL_MILE, 2)
        # Spherical triangular inequality
        self.assertTrue(dab * dab + dac * dac > dbc * dbc)
        d = SimplePoint(90, 0)
        e = SimplePoint(0, 90)
        dad = orthodromic_distance(a, d)
        dae = orthodromic_distance(a, e)
        dde = orthodromic_distance(d, e)
        self.assertAlmostEqual(dad, dae, 3)
        self.assertAlmostEqual(dae, dde, 3)
        self.assertAlmostEqual(dad, dde, 3)
        f = SimplePoint(45, 0)
        daf = orthodromic_distance(a, f)
        self.assertAlmostEqual(daf * 2, dad, 3)
        g = SimplePoint(45.0001, 0)
        h = SimplePoint(45, 0.0001)
        dfg = orthodromic_distance(f, g)
        dfh = orthodromic_distance(f, h)
        dgh = orthodromic_distance(g, h)
        self.assertAlmostEqual(dfg * math.cos(math.radians(45)), dfh, 3)
        # Not perfectly equals, but for small distance should hold
        self.assertAlmostEqual(dfg * dfg + dfh * dfh, dgh * dgh, 2)

    def test_seg_distance(self):
        a = SimplePoint(0, 0)
        daaa = orthodromic_seg_distance(a, a, a)
        self.assertAlmostEqual(daaa, 0.0, 3)
        b = SimplePoint(1, 0)
        daab = orthodromic_seg_distance(a, a, b)
        self.assertAlmostEqual(daab, 0.0, 3)
        dbab = orthodromic_seg_distance(b, a, b)
        self.assertAlmostEqual(dbab, 0.0, 3)
        c = SimplePoint(0.5, 0)
        dcab = orthodromic_seg_distance(c, a, b)
        self.assertAlmostEqual(dcab, 0.0, 3)
        d = SimplePoint(-1, 0)
        ddab = orthodromic_seg_distance(d, a, b)
        self.assertAlmostEqual(ddab / 60, self._NAUTICAL_MILE, 2)
        e = SimplePoint(2, 0)
        deab = orthodromic_seg_distance(e, a, b)
        self.assertAlmostEqual(deab / 60, self._NAUTICAL_MILE, 2)
        f = SimplePoint(0.01, 1)
        dfab = orthodromic_seg_distance(f, a, b)
        self.assertAlmostEqual(dfab / 60, self._NAUTICAL_MILE, 2)
        g = SimplePoint(1, 1)
        h = SimplePoint(0.5, 0.5)
        dhag = orthodromic_seg_distance(h, a, g)
        self.assertAlmostEqual(dhag, 0, 3)
        # Please note that the following is true only because
        # the distance is an approximation on the equirectangular projection.
        dbag = orthodromic_seg_distance(b, a, g)
        self.assertAlmostEqual(dbag / 60 * math.sqrt(2), self._NAUTICAL_MILE, 0)

if __name__ == '__main__':
    unittest.main()
