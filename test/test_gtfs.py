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

import unittest

from sqlalchemy.orm import clear_mappers

from gtfslib.spatial import orthodromic_distance
from gtfslib.dao import Dao

# Location of GTFS files to tests.
# This unit-test is not dependent on the content of a GTFS file.
# It just check for some generic assumptions that should be valid for any GTFS.
GTFS_LIST = [ "test/mini.gtfs.zip", "test/dummy.gtfs.zip", "test/sample-feed.zip" ]

DAO_URL = ""
# Set this to true to activate SQL logging
SQL_LOG = False

class TestGtfs(unittest.TestCase):

    def _test_one_gtfs(self, gtfs):
        clear_mappers()
        dao = Dao(DAO_URL, sql_logging=SQL_LOG)
        dao.load_gtfs(gtfs)

        # Check stop time normalization and interpolation
        for trip in dao.trips(prefetch_stop_times=True):
            stopseq = 0
            n_stoptimes = len(trip.stop_times)
            last_stop = None
            distance = trip.stop_times[0].shape_dist_traveled
            last_stoptime = None
            last_interpolated_speed = None
            for stoptime in trip.stop_times:
                self.assertTrue(stoptime.stop_sequence == stopseq)
                if stopseq == 0:
                    self.assertTrue(stoptime.arrival_time is None)
                else:
                    self.assertTrue(stoptime.arrival_time is not None)
                if stopseq == n_stoptimes - 1:
                    self.assertTrue(stoptime.departure_time is None)
                else:
                    self.assertTrue(stoptime.departure_time is not None)
                if last_stop is not None:
                    distance += orthodromic_distance(last_stop, stoptime.stop)
                last_stop = stoptime.stop
                if trip.shape is not None:
                    self.assertTrue(stoptime.shape_dist_traveled >= distance)
                else:
                    self.assertAlmostEqual(stoptime.shape_dist_traveled, distance, 1)
                stopseq += 1
                if stoptime.interpolated or (last_stoptime is not None and last_stoptime.interpolated):
                    dist = stoptime.shape_dist_traveled - last_stoptime.shape_dist_traveled
                    time = stoptime.arrival_time - last_stoptime.departure_time
                    speed = dist * 1.0 / time
                    if last_interpolated_speed is not None:
                        self.assertAlmostEqual(speed, last_interpolated_speed, 2)
                    last_interpolated_speed = speed
                if not stoptime.interpolated:
                    last_interpolated_speed = None
                last_stoptime = stoptime

        # Get all hops
        hops = dao.hops()
        nhops = 0
        for st1, st2 in hops:
            self.assertTrue(st1.stop_sequence + 1 == st2.stop_sequence)
            self.assertTrue(st1.trip == st2.trip)
            nhops += 1

        # Get hops with a delta of 2
        hops = dao.hops(delta=2)
        nhops2 = 0
        for st1, st2 in hops:
            self.assertTrue(st1.stop_sequence + 2 == st2.stop_sequence)
            self.assertTrue(st1.trip == st2.trip)
            nhops2 += 1
        ntrips = len(list(dao.trips()))
        # Assume all trips have len > 2
        self.assertTrue(nhops == nhops2 + ntrips)

        # Test shape_dist_traveled on stoptimes
        for trip in dao.trips():
            # Assume no shapes for now
            distance = 0.0
            last_stop = None
            for stoptime in trip.stop_times:
                if last_stop is not None:
                    distance += orthodromic_distance(last_stop, stoptime.stop)
                last_stop = stoptime.stop
                if trip.shape:
                    self.assertTrue(stoptime.shape_dist_traveled >= distance)
                else:
                    self.assertAlmostEqual(stoptime.shape_dist_traveled, distance, 2)

        # Test shape normalization
        for shape in dao.shapes():
            distance = 0.0
            last_pt = None
            ptseq = 0
            for point in shape.points:
                if last_pt is not None:
                    distance += orthodromic_distance(last_pt, point)
                last_pt = point
                self.assertAlmostEqual(point.shape_dist_traveled, distance, 2)
                self.assertTrue(point.shape_pt_sequence == ptseq)
                ptseq += 1

        # Check zone-stop relationship
        for zone in dao.zones(prefetch_stops=True):
            for stop in zone.stops:
                self.assertTrue(stop.zone == zone)
        for stop in dao.stops():
            if stop.zone:
                self.assertTrue(stop in stop.zone.stops)

    def test_all_gtfs(self):
        for gtfs in GTFS_LIST:
            print("Testing %s" % gtfs)
            self._test_one_gtfs(gtfs)

if __name__ == '__main__':
    unittest.main()
