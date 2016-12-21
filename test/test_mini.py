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

from gtfslib.model import Trip
from gtfslib.dao import Dao

# Location of mini.gtfs.zip.
# This unit-test is highly dependent on the CONTENT of this GTFS.
MINI_GTFS = "test/mini.gtfs.zip"

DAO_URL = ""
# To unit-test with postgresql, create a db "gtfs" with user "gtfs" and uncomment the following line:
# DAO_URL = "postgresql://gtfs@localhost/gtfs"
# Set this to true to activate SQL logging
SQL_LOG = False

class TestMiniGtfs(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        clear_mappers()

    def test_gtfs_data(self):
        dao = Dao(DAO_URL, sql_logging=SQL_LOG)
        dao.load_gtfs(MINI_GTFS)

        # Check feed
        feed = dao.feed()
        self.assertTrue(feed.feed_id == "")
        self.assertTrue(feed.feed_publisher_name is None)
        self.assertTrue(feed.feed_publisher_url is None)
        self.assertTrue(feed.feed_contact_email is None)
        self.assertTrue(feed.feed_contact_url is None)
        self.assertTrue(feed.feed_start_date is None)
        self.assertTrue(feed.feed_end_date is None)
        self.assertTrue(len(dao.agencies()) == 1)
        self.assertTrue(len(dao.routes()) == 1)
        self.assertTrue(len(feed.agencies) == 1)
        self.assertTrue(len(feed.routes) == 1)

        # Check if optional route agency is set
        a = dao.agency("A")
        self.assertTrue(a is not None)
        self.assertTrue(len(a.routes) == 1)

        # Check for frequency-generated trips
        # They should all have the same delta
        trips = dao.trips(fltr=(Trip.frequency_generated == True), prefetch_stop_times=True)
        n_trips = 0
        deltas = {}
        for trip in trips:
            original_trip_id = trip.trip_id.rsplit('@', 1)[0]
            delta1 = []
            for st1, st2 in trip.hops():
                delta1.append(st2.arrival_time - st1.departure_time)
            delta2 = deltas.get(original_trip_id)
            if delta2 is not None:
                self.assertTrue(delta1 == delta2)
            else:
                deltas[original_trip_id] = delta1
            n_trips += 1
        self.assertTrue(n_trips == 8)

    def test_whitespace_stripping(self):
        dao = Dao(DAO_URL, sql_logging=SQL_LOG)
        dao.load_gtfs(MINI_GTFS)

        # Check if whitespace stripping works
        a = dao.agency("A")
        self.assertTrue(a.agency_name == "Mini Agency")
        self.assertTrue(a.agency_lang == "en")

    def test_hops(self):
        dao = Dao(DAO_URL, sql_logging=SQL_LOG)
        dao.load_gtfs(MINI_GTFS)

        # Get all hops
        hops = dao.hops()
        nhops = 0
        for st1, st2 in hops:
            self.assertTrue(st1.stop_sequence + 1 == st2.stop_sequence)
            self.assertTrue(st1.trip == st2.trip)
            nhops += 1
        # 2 standard trips + 2 frequency generated (8 total)
        self.assertTrue(nhops == 2 * 2 + 8 * 2)

        # Get all hops with a distance <= 70km
        hops = dao.hops(fltr=(dao.hop_second().shape_dist_traveled - dao.hop_first().shape_dist_traveled <= 70000))
        nhops1 = 0
        for st1, st2 in hops:
            self.assertTrue(st1.stop_sequence + 1 == st2.stop_sequence)
            self.assertTrue(st1.trip == st2.trip)
            self.assertTrue(st2.shape_dist_traveled - st1.shape_dist_traveled <= 70000)
            nhops1 += 1

        # Get all hops with a distance > 70km
        hops = dao.hops(fltr=(dao.hop_second().shape_dist_traveled - dao.hop_first().shape_dist_traveled > 70000))
        nhops2 = 0
        for st1, st2 in hops:
            self.assertTrue(st1.stop_sequence + 1 == st2.stop_sequence)
            self.assertTrue(st1.trip == st2.trip)
            self.assertTrue(st2.shape_dist_traveled - st1.shape_dist_traveled > 70000)
            nhops2 += 1
        self.assertTrue(nhops == nhops1 + nhops2)

        # Get all hops with a time +/- 1h
        hops = dao.hops(fltr=(dao.hop_second().arrival_time - dao.hop_first().departure_time >= 3600))
        for st1, st2 in hops:
            self.assertTrue(st2.arrival_time - st1.departure_time >= 3600)
        hops = dao.hops(fltr=(dao.hop_second().arrival_time - dao.hop_first().departure_time < 3600))
        for st1, st2 in hops:
            self.assertTrue(st2.arrival_time - st1.departure_time < 3600)

        # Get hops with a delta of 2
        hops = dao.hops(delta=2)
        for st1, st2 in hops:
            self.assertTrue(st1.stop_sequence + 2 == st2.stop_sequence)
            self.assertTrue(st1.trip == st2.trip)

if __name__ == '__main__':
    unittest.main()
