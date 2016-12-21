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

from gtfslib.spatial import RectangularArea
from sqlalchemy.orm import clear_mappers

from gtfslib.dao import Dao
from gtfslib.model import CalendarDate, FeedInfo, Agency, Route, Calendar, Stop, \
    Trip, StopTime, Transfer, Shape, ShapePoint, Zone, FareAttribute, FareRule

class TestDao(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        clear_mappers()

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
        
        self.assertTrue(len(list(dao.stops())) == 7)

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
        t1.direction_id = 0
        t11 = StopTime("F1", "T1", "S1", 0, 28800, 28800, 0.0)
        t12 = StopTime("F1", "T1", "S2", 1, 29400, 29400, 0.0)
        t13 = StopTime("F1", "T1", "S3", 2, 30000, 30000, 0.0)
        t2 = Trip("F1", "T2", "R1", "C1")
        t2.direction_id = 1
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

        trips = list(dao.trips(fltr=Trip.direction_id == 0))
        self.assertTrue(len(trips) == 1)
        trips = list(dao.trips(fltr=Trip.direction_id == 1))
        self.assertTrue(len(trips) == 1)

    def test_stop_station(self):
        dao = Dao()
        f1 = FeedInfo("F1")
        sa = Stop("F1", "SA", "Station A", 45.0000, 0.0000)
        sa1 = Stop("F1", "SA1", "Stop A1", 45.0001, 0.0001)
        sa1.parent_station_id = 'SA'
        sb = Stop("F1", "SB", "Station B", 45.0002, 0.0002)
        sb1 = Stop("F1", "SB1", "Stop B1", 45.0003, 0.0003)
        sb1.parent_station_id = 'SB'
        sb2 = Stop("F1", "SB2", "Stop B2", 45.0002, 0.0003)
        sb2.parent_station_id = 'SB'
        a1 = Agency("F1", "A1", "Agency 1", "url1", "Europe/Paris")
        r1 = Route("F1", "R1", "A1", Route.TYPE_BUS)
        c1 = Calendar("F1", "C1")
        t1 = Trip("F1", "T1", "R1", "C1")
        st1a = StopTime("F1", "T1", "SA1", 0, None, 3600, 0.0)
        st1b = StopTime("F1", "T1", "SB1", 1, 3800, None, 100.0)
        dao.add_all([ f1, sa, sa1, sb, sb1, sb2, a1, r1, c1, t1, st1a, st1b ])

        stops = list(dao.stops(fltr=(Agency.agency_id=='A1')))
        self.assertTrue(len(stops) == 2)
        self.assertTrue(sa1 in stops)
        self.assertTrue(sb1 in stops)

        stops = list(dao.stops(fltr=(Stop.parent_station_id=='SA')))
        self.assertTrue(len(stops) == 1)
        self.assertTrue(sa1 in stops)

        stops = list(dao.stops(fltr=(Stop.parent_station_id=='SB')))
        self.assertTrue(len(stops) == 2)
        self.assertTrue(sb1 in stops)
        self.assertTrue(sb2 in stops)

    def test_transfers(self):
        dao = Dao()
        f1 = FeedInfo("F1")
        s1 = Stop("F1", "S1", "Stop 1", 45.0000, 0.0000)
        s2 = Stop("F1", "S2", "Stop 2", 45.0001, 0.0001)
        s3 = Stop("F1", "S3", "Stop 3", 45.0002, 0.0002)
        t12 = Transfer("F1", "S1", "S2")
        t21 = Transfer("F1", "S2", "S1")
        t23 = Transfer("F1", "S2", "S3", transfer_type=Transfer.TRANSFER_TIMED, min_transfer_time=180)
        t32 = Transfer("F1", "S3", "S2", transfer_type=Transfer.TRANSFER_TIMED, min_transfer_time=120)
        t13 = Transfer("F1", "S1", "S3", transfer_type=Transfer.TRANSFER_NONE)
        a1 = Agency("F1", "A1", "Agency 1", "url1", "Europe/Paris")
        a2 = Agency("F1", "A2", "Agency 2", "url2", "Europe/London")
        r1 = Route("F1", "R1", "A1", Route.TYPE_BUS)
        r2 = Route("F1", "R2", "A2", Route.TYPE_BUS)
        c1 = Calendar("F1", "C1")
        t1 = Trip("F1", "T1", "R1", "C1")
        t2 = Trip("F1", "T2", "R2", "C1")
        st1a = StopTime("F1", "T1", "S1", 0, None, 3600, 0.0)
        st1b = StopTime("F1", "T1", "S2", 1, 3800, None, 100.0)
        st2a = StopTime("F1", "T2", "S1", 0, None, 4600, 0.0)
        st2b = StopTime("F1", "T2", "S3", 1, 4800, None, 100.0)
        dao.add_all([ f1, s1, s2, s3, t12, t21, t23, t32, t13, a1, a2, r1, r2, c1, t1, t2, st1a, st1b, st2a, st2b ])

        self.assertTrue(len(dao.transfers()) == 5)

        timed_transfers = dao.transfers(fltr=(Transfer.transfer_type == Transfer.TRANSFER_TIMED))
        self.assertTrue(len(timed_transfers) == 2)
        for transfer in timed_transfers:
            self.assertTrue(transfer.transfer_type == Transfer.TRANSFER_TIMED)

        s1_from_transfers = dao.transfers(fltr=(dao.transfer_from_stop().stop_name == "Stop 1"))
        self.assertTrue(len(s1_from_transfers) == 2)
        for transfer in s1_from_transfers:
            self.assertTrue(transfer.from_stop.stop_name == "Stop 1")

        s1_fromto_transfers = dao.transfers(fltr=((dao.transfer_from_stop().stop_name == "Stop 1") | (dao.transfer_to_stop().stop_name == "Stop 1")))
        self.assertTrue(len(s1_fromto_transfers) == 3)
        for transfer in s1_fromto_transfers:
            self.assertTrue(transfer.from_stop.stop_name == "Stop 1" or transfer.to_stop.stop_name == "Stop 1")

        s1 = dao.stop("S1", feed_id="F1")
        self.assertTrue(len(s1.from_transfers) == 2)
        self.assertTrue(len(s1.to_transfers) == 1)
        for transfer in s1.from_transfers:
            if transfer.to_stop.stop_id == "S2":
                self.assertTrue(transfer.transfer_type == Transfer.TRANSFER_DEFAULT)
            elif transfer.to_stop.stop_id == "S3":
                self.assertTrue(transfer.transfer_type == Transfer.TRANSFER_NONE)

        a1_stops = list(dao.stops(fltr=(Agency.agency_id=='A1')))
        self.assertTrue(len(a1_stops) == 2)
        self.assertTrue(s1 in a1_stops)
        self.assertTrue(s2 in a1_stops)

    def test_areas(self):
        dao = Dao()
        f1 = FeedInfo("F1")
        s1 = Stop("F1", "S1", "Stop 1", 45.0, 0.0)
        s2 = Stop("F1", "S2", "Stop 2", 45.1, 0.1)
        s3 = Stop("F1", "S3", "Stop 3", 45.2, 0.2)
        dao.add_all([ f1, s1, s2, s3 ])

        # Rectangular area
        stops = list(dao.stops(fltr=dao.in_area(RectangularArea(0, 0, 1, 1))))
        self.assertTrue(len(stops) == 0)
        stops = list(dao.stops(fltr=dao.in_area(RectangularArea(-90, -180, 90, 180))))
        self.assertTrue(len(stops) == 3)
        stops = list(dao.stops(fltr=dao.in_area(RectangularArea(45.05, 0.05, 45.15, 0.15))))
        self.assertTrue(len(stops) == 1)
        self.assertTrue(stops[0].stop_id == 'S2')

    def test_shapes(self):
        dao = Dao()
        f1 = FeedInfo("")
        a1 = Agency("", "A1", "Agency 1", agency_url="http://www.agency.fr/", agency_timezone="Europe/Paris")
        r1 = Route("", "R1", "A1", 3, route_short_name="R1", route_long_name="Route 1")
        c1 = Calendar("", "C1")
        c1.dates = [ CalendarDate.ymd(2016, 1, 31), CalendarDate.ymd(2016, 2, 1) ]
        s1 = Stop("", "S1", "Stop 1", 45.0, 0.0)
        s2 = Stop("", "S2", "Stop 2", 45.1, 0.1)
        s3 = Stop("", "S3", "Stop 3", 45.2, 0.2)
        t1 = Trip("", "T1", "R1", "C1")
        t1.stop_times = [ StopTime(None, None, "S1", 0, 28800, 28800, 0.0),
                          StopTime(None, None, "S2", 1, 29400, 29400, 2.0),
                          StopTime(None, None, "S3", 2, 30000, 30000, 4.0) ]
        t2 = Trip("", "T2", "R1", "C1")
        t2.stop_times = [ StopTime(None, None, "S2", 0, 30600, 30600, 0.0),
                          StopTime(None, None, "S1", 1, 31000, 31000, 1.0) ]
        sh1 = Shape("", "Sh1")
        sh1.points = [ ShapePoint(None, None, 0, 45.00, 0.00, 0.0),
                      ShapePoint(None, None, 1, 45.05, 0.10, 1.0),
                      ShapePoint(None, None, 2, 45.10, 0.10, 2.0),
                      ShapePoint(None, None, 3, 45.15, 0.20, 3.0),
                      ShapePoint(None, None, 4, 45.20, 0.20, 4.0) ]
        t1.shape = sh1
        dao.add_all([ f1, a1, r1, c1, s1, s2, s3, t1, t2, sh1 ])
        dao.commit()

        t = dao.trip("T1")
        self.assertTrue(t.shape.shape_id == "Sh1")
        self.assertTrue(len(t.shape.points) == 5)
        t = dao.trip("T2")
        self.assertTrue(t.shape == None)

    def test_zones(self):
        dao = Dao()
        f1 = FeedInfo("")
        z1 = Zone("", "Z1")
        s1 = Stop("", "S1", "Stop 1", 45.0, 0.0)
        s2 = Stop("", "S2", "Stop 2", 45.1, 0.1, zone_id="Z1")
        s3 = Stop("", "S3", "Stop 3", 45.2, 0.2)
        s3.zone = z1
        dao.add_all([ f1, z1, s1, s2, s3 ])
        dao.commit()

        self.assertTrue(len(dao.zones()) == 1)
        z = dao.zone("Z1")
        self.assertTrue(len(z.stops) == 2)
        for stop in z.stops:
            self.assertTrue(stop.zone == z)
        s = dao.stop("S1")
        self.assertTrue(s.zone == None)
        s = dao.stop("S2")
        self.assertTrue(s.zone == z)
        s = dao.stop("S3")
        self.assertTrue(s.zone == z)

    def test_fares(self):
        dao = Dao()
        f1 = FeedInfo("")
        a1 = Agency("", "A1", "Agency 1", agency_url="http://www.agency.fr/", agency_timezone="Europe/Paris")
        r1 = Route("", "R1", "A1", 3, route_short_name="R1", route_long_name="Route 1")
        r2 = Route("", "R2", "A1", 3, route_short_name="R2", route_long_name="Route 2")
        z1 = Zone("", "Z1")
        z2 = Zone("", "Z2")
        fare1 = FareAttribute("", "F1", 1.0, "EUR", FareAttribute.PAYMENT_ONBOARD, None, None)
        fare2 = FareAttribute("", "F2", 2.0, "EUR", FareAttribute.PAYMENT_BEFOREBOARDING, 3, 3600)
        rule1 = FareRule("", "F1", route_id="R1")
        rule2 = FareRule("", "F1", origin_id="Z1", destination_id="Z2")
        dao.add_all([ f1, a1, r1, r2, z1, z2, fare1, fare2, rule1, rule2 ])
        dao.commit()

        self.assertTrue(len(dao.fare_attributes()) == 2)
        self.assertTrue(len(dao.fare_rules(fltr=(FareRule.route == r1))) == 1)
        self.assertTrue(len(dao.fare_rules(fltr=(FareRule.route == r2))) == 0)
        self.assertTrue(len(dao.fare_rules(fltr=(FareRule.origin == z1))) == 1)
        fare = dao.fare_attribute("F1")
        self.assertTrue(len(fare.fare_rules) == 2)
        fare = dao.fare_attribute("F2")
        self.assertTrue(len(fare.fare_rules) == 0)

        # Test equivalence and hash on primary keys for rule
        fr1a = FareRule("", "F1", route_id="R", origin_id="ZO", destination_id="ZD", contains_id=None)
        fr1b = FareRule("", "F1", route_id="R", origin_id="ZO", destination_id="ZD", contains_id=None)
        fr2 = FareRule("", "F1", route_id="R", origin_id="ZO", destination_id=None, contains_id="ZD")
        ruleset = set()
        ruleset.add(fr1a)
        ruleset.add(fr2)
        ruleset.add(fr1b)
        self.assertTrue(len(ruleset) == 2)
        self.assertTrue(fr1a == fr1b)
        self.assertTrue(fr1a != fr2)

if __name__ == '__main__':
    unittest.main()
