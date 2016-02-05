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
import math

# Radius of earth in meters
EARTH_RADIUS = 6371000

def orthodromic_distance(a, b):
    # Use Haversine formula
    lon_a, lat_a, lon_b, lat_b = map(math.radians, [a.lon(), a.lat(), b.lon(), b.lat()])
    dlon = lon_b - lon_a 
    dlat = lat_b - lat_a 
    c = 2 * math.asin(math.sqrt(math.sin(dlat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(dlon / 2) ** 2))
    return c * EARTH_RADIUS

"""
@return A 2-tuple composed of
            1) the distance in meter from the point p to the segment [ab],
            2) the distance in meter from a to the clamped projection of p on [ab].
            The clamped projection is the standard projected point if it lies on the
            segment, or one of the extremities of the segment if not.
"""
def orthodromic_seg_distance(p, a, b):
    # Use approximate equirectangular projection
    x_p = math.radians(p.lat())
    cos_p = math.cos(x_p)
    y_p, y_a, y_b = map(lambda q: math.radians(q.lon()) * cos_p, [p, a, b])
    x_a, x_b = map(lambda q: math.radians(q.lat()), [a, b])
    # Compute [AB] length
    l2 = (x_a - x_b) * (x_a - x_b) + (y_a - y_b) * (y_a - y_b)
    if l2 == 0:
        # Pathological d(AB)=0 case, d = d(PA)
        d2 = (x_p - x_a) * (x_p - x_a) + (y_p - y_a) * (y_p - y_a)
        # Any value of t will do
        t = 0
    else:
        # Compute t, linear coordinate of C in the [AB] vector basis
        # and where C is the projection of P on line (AB).
        t = ((x_p - x_a) * (x_b - x_a) + (y_p - y_a) * (y_b - y_a)) / l2
        if t < 0:
            # C outside [AB] on A side: d = d(PA)
            d2 = (x_p - x_a) * (x_p - x_a) + (y_p - y_a) * (y_p - y_a)
            # Clamp
            t = 0
        elif t > 1:
            # C outside [AB] on B side: d = d(PB)
            d2 = (x_p - x_b) * (x_p - x_b) + (y_p - y_b) * (y_p - y_b)
            # Clamp
            t = 1
        else:
            # C inside [AB]: d = d(PC), C = A + t.B
            xC = x_a + t * (x_b - x_a)
            yC = y_a + t * (y_b - y_a)
            d2 = (x_p - xC) * (x_p - xC) + (y_p - yC) * (y_p - yC)
    return EARTH_RADIUS * math.sqrt(d2), EARTH_RADIUS * math.sqrt(l2) * t

class DistanceCache(object):
    
    def __init__(self):
        self._cache = {}
    
    def orthodromic_distance(self, a, b):
        key = (a.lat(), a.lon(), b.lat(), b.lon())
        if key in self._cache:
            return self._cache[key]
        d = orthodromic_distance(a, b)
        self._cache[key] = d
        return d

class RectangularArea(object):
    
    def __init__(self, min_lat, min_lon, max_lat, max_lon):
        self.min_lat = min_lat
        self.min_lon = min_lon
        self.max_lat = max_lat
        self.max_lon = max_lon

    def __repr__(self):
        return "<%s(%f,%f)-(%f,%f)>" % (
                self.__class__.__name__, self.min_lat, self.min_lon, self.max_lat, self.max_lon)
        
# TODO Create circular area (=center+radius)?
