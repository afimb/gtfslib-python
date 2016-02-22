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
import pyqtree
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


class SpatialClusterizer(object):
    """This class is meant to group stops in clusters based on distance proximity.
       It will group all stops that are nearer than D0 meters."""

    def __init__(self, D0):
        self._D0 = 1. * D0
        bbox = (-180, -90, 180, 90)
        self._spidx = pyqtree.Index(bbox)
        self._points = []
        self._clusters = None
        self._cluster_values = []

    def add_point(self, p):
        if self._clusters:
            raise Exception("Can't add point after clusterized has been called")
        self._spidx.insert(p, (p.lon(), p.lat(),
                               p.lon(), p.lat()))
        self._points.append(p)

    def add_points(self, ps):
        for p in ps:
            self.add_point(p)

    def clusterize(self):
        self._clusters = {}
        for p in self._points:
            self._clusters[p] = set([p])
        for p1 in self._points:
            # Compute bounds in lat,lon degree of D0 square around stop
            cos_lat = math.cos(math.radians(p.lat()))
            dlon = math.degrees(self._D0 / EARTH_RADIUS * cos_lat)
            dlat = math.degrees(self._D0 / EARTH_RADIUS)
            bbox = (p1.lon() - dlon, p1.lat() - dlat,
                    p1.lon() + dlon, p1.lat() + dlat)
            nearby = self._spidx.intersect(bbox)
            for p2 in nearby:
                d = orthodromic_distance(p1, p2)
                if d > self._D0:
                    continue
                c1 = self._clusters.get(p1, set())
                c2 = self._clusters.get(p2, set())
                if c1 is c2:
                    # Already same cluster
                    continue
                # Merge cluster c1 and c2
                c3 = c1 | c2
                for p in c3:
                    self._clusters[p] = c3
        seen_points = set()
        for k, cluster in self._clusters.items():
            for p in cluster:
                break;
            if p in seen_points:
                continue
            self._cluster_values.append(cluster)
            seen_points.add(p)

    def cluster_of(self, p):
        return self._clusters.get(p)

    def in_same_cluster(self, p1, p2):
        c1 = self._clusters.get(p1)
        c2 = self._clusters.get(p2)
        if c1 is None or c2 is None:
            return False
        return c1 is c2

    def clusters(self):
        return self._cluster_values
