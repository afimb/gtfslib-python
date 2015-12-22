# -*- coding: utf-8 -*-
"""
@author: Laurent GRÉGOIRE <laurent.gregoire@mecatran.com>
"""
import math


def orthodromic_distance(a, b):
    # Use Haversine formula
    lon_a, lat_a, lon_b, lat_b = map(math.radians, [a.lon(), a.lat(), b.lon(), b.lat()])
    dlon = lon_b - lon_a 
    dlat = lat_b - lat_a 
    c = 2 * math.asin(math.sqrt(math.sin(dlat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(dlon / 2) ** 2))
    # Radius of earth in km.
    EARTH_RADIUS = 6371
    return c * EARTH_RADIUS * 1000

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
