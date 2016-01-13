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

from gtfslib.dao import Dao
from gtfslib.model import CalendarDate, FeedInfo, Agency, Route, Calendar, Stop, \
    Trip, StopTime


class TestDao(unittest.TestCase):

    def test_entities_creation(self):
        dao = Dao()
        f1 = FeedInfo("F1")
        a1 = Agency("F1", "A1", "Agency 1", agency_url="http://www.agency.fr/", agency_timezone="Europe/Paris")
        r1 = Route("F1", "R1", "A1", 3, route_short_name="R1", route_long_name="Route 1")
        r2 = Route("F1", "R2", "A1", 3, route_short_name="R2")
        c1 = Calendar("F1", "C1")
        c1.dates = [ CalendarDate.ymd(2015, 11, 13), CalendarDate.ymd(2015, 11, 14) ]
        dao.add_all([ f1, a1, r1, r2, c1 ])

        self.assertTrue(len(dao.feeds()) == 1)
        self.assertTrue(len(dao.agencies()) == 1)
        a1b = dao.agency("A1", feed_id="F1", prefetch_routes=True)
        self.assertTrue(a1b.agency_name == "Agency 1")
        self.assertTrue(len(a1b.routes) == 2)
        r1b = dao.route("R1", feed_id="F1")
        self.assertTrue(r1b.route_short_name == "R1")
        self.assertTrue(r1b.route_long_name == "Route 1")
        self.assertTrue(r1b.route_type == 3)
        r42 = dao.route("R42", feed_id="F1")
        self.assertTrue(r42 is None)
        
    def test_entities_deletion(self):
        dao = Dao()
        f1 = FeedInfo("F1")
        a1 = Agency("F1", "A1", "Agency 1", agency_url="http://www.agency.fr/", agency_timezone="Europe/Paris")
        dao.add_all([ f1, a1 ])
        for feed in dao.feeds():
            dao.delete(feed)
        self.assertTrue(len(dao.feeds()) == 0)

    def test_stop_station_multi_feed(self):
        dao = Dao()
        fa = FeedInfo("FA")
        fb = FeedInfo("FB")
        sa = Stop("FA", "S", "Station A", 45.0, 0.0, location_type=Stop.TYPE_STATION)
        sa1 = Stop("FA", "S1", "Stop A1", 45.0, 0.0, parent_station_id="S")
        sa2 = Stop("FA", "S2", "Stop A2", 45.0, 0.1, parent_station_id="S")
        sa3 = Stop("FA", "S3", "Stop A3", 45.0, 0.2)
        sb = Stop("FB", "S", "Station B", 45.0, 0.0, location_type=Stop.TYPE_STATION)
        sb1 = Stop("FB", "S1", "Stop B1", 45.0, 0.0, parent_station_id="S")
        sb2 = Stop("FB", "S2", "Stop B2", 45.0, 0.1, parent_station_id="S")
        dao.add_all([ fa, fb, sa, sa1, sa2, sa3, sb1, sb2, sb ])
        
        sa = dao.stop("S", feed_id="FA")
        self.assertTrue(sa.stop_name == "Station A")
        self.assertTrue(len(sa.sub_stops) == 2)
        for ssa in sa.sub_stops:
            self.assertTrue(ssa.stop_name.startswith("Stop A"))
            self.assertTrue(ssa.parent_station.stop_name == "Station A")
        
        sa1 = dao.stop("S1", feed_id="FA")
        self.assertTrue(sa1.stop_name == "Stop A1")
        self.assertTrue(sa1.parent_station.stop_name == "Station A")
        
        self.assertTrue(len(dao.stops()) == 7)

    def test_route_agency_multi_feed(self):
        dao = Dao()
        fa = FeedInfo("FA")
        aa1 = Agency("FA", "A", "Agency A", agency_url="http://www.agency.fr/", agency_timezone="Europe/Paris")
        ar1 = Route("FA", "R", "A", 3, route_short_name="RA", route_long_name="Route A")
        ar2 = Route("FA", "R2", "A", 3, route_short_name="RA2", route_long_name="Route A2")
        fb = FeedInfo("FB")
        ba1 = Agency("FB", "A", "Agency B", agency_url="http://www.agency.fr/", agency_timezone="Europe/Paris")
        br1 = Route("FB", "R", "A", 3, route_short_name="RB", route_long_name="Route B")
        dao.add_all([ fa, aa1, ar1, ar2, fb, ba1, br1 ])
        
        fa = dao.feed("FA")
        self.assertTrue(len(fa.agencies) == 1)
        for a in fa.agencies:
            self.assertTrue(a.agency_name == "Agency A")
        self.assertTrue(len(fa.routes) == 2)
        for r in fa.routes:
            self.assertTrue(r.route_short_name.startswith("RA"))
            self.assertTrue(r.agency.agency_name == "Agency A")

    def test_trip(self):
        dao = Dao()
        f1 = FeedInfo("F1")
        a1 = Agency("F1", "A1", "Agency 1", agency_url="http://www.agency.fr/", agency_timezone="Europe/Paris")
        r1 = Route("F1", "R1", "A1", 3, route_short_name="R1", route_long_name="Route 1")
        c1 = Calendar("F1", "C1")
        c1.dates = [ d for d in CalendarDate.range(CalendarDate.ymd(2016, 1, 1), CalendarDate.ymd(2016, 1, 31).next_day()) ]
        s1 = Stop("F1", "S1", "Stop 1", 45.0, 0.0)
        s2 = Stop("F1", "S2", "Stop 2", 45.1, 0.1)
        s3 = Stop("F1", "S3", "Stop 3", 45.2, 0.2)
        t1 = Trip("F1", "T1", "R1", "C1")
        t11 = StopTime("F1", "T1", "S1", 0, 28800, 28800, 0.0)
        t12 = StopTime("F1", "T1", "S2", 1, 29400, 29400, 0.0)
        t13 = StopTime("F1", "T1", "S3", 2, 30000, 30000, 0.0)
        t2 = Trip("F1", "T2", "R1", "C1")
        # Order is not important for now
        t2.stop_times.append(StopTime(None, None, "S1", 1, 31000, 31000, 0.0))
        t2.stop_times.append(StopTime(None, None, "S2", 0, 30600, 30600, 0.0))

        dao.add_all([ f1, a1, r1, c1, s1, s2, s3, t1, t11, t12, t13, t2 ])
        # Commit is needed to re-order stop times of T2
        dao.commit()

        cal = dao.calendar("C1", feed_id="F1")
        for trip in cal.trips:
            self.assertTrue(trip.calendar.service_id == "C1")
            for stoptime in trip.stop_times:
                self.assertTrue(stoptime.trip.calendar.service_id == "C1")
            
        stop = dao.stop("S2", feed_id="F1")
        for stoptime in stop.stop_times:
            self.assertTrue(stoptime.stop.stop_id == "S2")
            self.assertTrue(stoptime.trip.trip_id.startswith("T"))
            
        trip = dao.trip("T1", feed_id="F1")
        self.assertTrue(len(trip.stop_times) == 3)

        trip = dao.trip("T2", feed_id="F1")
        self.assertTrue(len(trip.stop_times) == 2)

        for trip in dao.trips(prefetch_stop_times=True):
            last_stop_seq = -1
            for stoptime in trip.stop_times:
                self.assertTrue(stoptime.stop_sequence > last_stop_seq)
                last_stop_seq = stoptime.stop_sequence

        for trip in dao.trips():
            for stoptime1, stoptime2 in trip.hops():
                self.assertTrue(stoptime1.trip == stoptime2.trip)
                self.assertTrue(stoptime1.stop_sequence + 1 == stoptime2.stop_sequence)

if __name__ == '__main__':
    unittest.main()
