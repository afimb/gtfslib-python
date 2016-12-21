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

import datetime
import unittest

from sqlalchemy.sql.expression import or_
from sqlalchemy.sql.functions import func
from sqlalchemy.orm import clear_mappers

from gtfslib.dao import Dao
from gtfslib.model import CalendarDate, Route, Calendar, Stop, \
    Trip, StopTime
from gtfslib.spatial import RectangularArea, SpatialClusterizer
from gtfslib.utils import gtfstime


# Location of dummy.gtfs.zip.
# This unit-test is highly dependent on the CONTENT of this GTFS.
DUMMY_GTFS = "test/dummy.gtfs.zip"

DAO_URL = ""
# To unit-test with postgresql, create a db "gtfs" with user "gtfs" and uncomment the following line:
# DAO_URL = "postgresql://gtfs@localhost/gtfs"
# Set this to true to activate SQL logging
SQL_LOG = False

class TestDummyGtfs(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        clear_mappers()

    def test_gtfs_data(self):
        dao = Dao(DAO_URL, sql_logging=False)
        dao.load_gtfs(DUMMY_GTFS)

        # Check feed
        feed = dao.feed()
        self.assertTrue(feed.feed_id == "")
        self.assertTrue(feed.feed_publisher_name == "Mecatran")
        self.assertTrue(feed.feed_publisher_url == "http://www.mecatran.com/")
        self.assertTrue(feed.feed_contact_email == "support@mecatran.com")
        self.assertTrue(feed.feed_lang == "fr")
        self.assertTrue(len(dao.agencies()) == 2)
        self.assertTrue(len(dao.routes()) == 3)
        self.assertTrue(len(feed.agencies) == 2)
        self.assertTrue(len(feed.routes) == 3)

        # Check agencies
        at = dao.agency("AT")
        self.assertTrue(at.agency_name == "Agency Train")
        self.assertTrue(len(at.routes) == 1)
        ab = dao.agency("AB")
        self.assertTrue(ab.agency_name == "Agency Bus")
        self.assertTrue(len(ab.routes) == 2)

        # Check calendars
        week = dao.calendar("WEEK")
        self.assertTrue(len(week.dates) == 253)
        summer = dao.calendar("SUMMER")
        self.assertTrue(len(summer.dates) == 42)
        mon = dao.calendar("MONDAY")
        self.assertTrue(len(mon.dates) == 49)
        sat = dao.calendar("SAT")
        self.assertTrue(len(sat.dates) == 53)
        for date in mon.dates:
            self.assertTrue(date.dow() == 0)
        for date in sat.dates:
            self.assertTrue(date.dow() == 5)
        for date in week.dates:
            self.assertTrue(date.dow() >= 0 and date.dow() <= 4)
        for date in summer.dates:
            self.assertTrue(date >= CalendarDate.ymd(2016, 7, 1) and date <= CalendarDate.ymd(2016, 8, 31))
        empty = dao.calendars(func.date(CalendarDate.date) == datetime.date(2016, 5, 1))
        # OR USE: empty = dao.calendars(CalendarDate.date == "2016-05-01")
        self.assertTrue(len(empty) == 0)
        july4 = CalendarDate.ymd(2016, 7, 4)
        summer_mon = dao.calendars(func.date(CalendarDate.date) == july4.date)
        n = 0
        for cal in summer_mon:
            self.assertTrue(july4 in cal.dates)
            n += 1
        self.assertTrue(n == 3)

        # Check stops
        sbq = dao.stop("BQ")
        self.assertAlmostEqual(sbq.stop_lat, 44.844, places=2)
        self.assertAlmostEqual(sbq.stop_lon, -0.573, places=2)
        self.assertTrue(sbq.stop_name == "Bordeaux Quinconces")
        n = 0
        for stop in dao.stops(Stop.stop_name.like("Gare%")):
            self.assertTrue(stop.stop_name.startswith("Gare"))
            n += 1
        self.assertTrue(n == 7)
        n = 0
        for stop in dao.stops(fltr=dao.in_area(RectangularArea(44.7, -0.6, 44.9, -0.4))):
            self.assertTrue(stop.stop_lat >= 44.7 and stop.stop_lat <= 44.9 and stop.stop_lon >= -0.6 and stop.stop_lon <= -0.4)
            n += 1
        self.assertTrue(n == 16)
        for station in dao.stops(Stop.location_type == Stop.TYPE_STATION):
            self.assertTrue(station.location_type == Stop.TYPE_STATION)
            self.assertTrue(len(station.sub_stops) >= 2)
            for stop in station.sub_stops:
                self.assertTrue(stop.parent_station == station)

        # Check zones
        z_inexistant = dao.zone("ZX")
        self.assertTrue(z_inexistant is None)
        z1 = dao.zone("Z1")
        self.assertEquals(16, len(z1.stops))
        z2 = dao.zone("Z2")
        self.assertEquals(4, len(z2.stops))

        # Check transfers
        transfers = dao.transfers()
        self.assertTrue(len(transfers) == 3)
        transfers = dao.transfers(fltr=(dao.transfer_from_stop().stop_id == 'GBSJB'))
        self.assertTrue(len(transfers) == 1)
        self.assertTrue(transfers[0].from_stop.stop_id == 'GBSJB')

        # Check routes
        tgv = dao.route("TGVBP")
        self.assertTrue(tgv.agency == at)
        self.assertTrue(tgv.route_type == 2)
        r1 = dao.route("BR")
        self.assertTrue(r1.route_short_name == "R1")
        self.assertTrue(r1.route_long_name == "Bus Red")
        n = 0
        for route in dao.routes(Route.route_type == 3):
            self.assertTrue(route.route_type == 3)
            n += 1
        self.assertTrue(n == 2)

        # Check trip for route
        n = 0
        trips = dao.trips(fltr=Route.route_type == Route.TYPE_BUS)
        for trip in trips:
            self.assertTrue(trip.route.route_type == Route.TYPE_BUS)
            n += 1
        self.assertTrue(n > 20)

        # Check trips on date
        trips = dao.trips(fltr=func.date(CalendarDate.date) == july4.date, prefetch_calendars=True)
        n = 0
        for trip in trips:
            self.assertTrue(july4 in trip.calendar.dates)
            n += 1
        self.assertTrue(n > 30)

    def test_non_overlapping_feeds(self):
        dao = Dao(DAO_URL, sql_logging=SQL_LOG)
        # Load twice the same data under two distinct namespaces
        dao.load_gtfs(DUMMY_GTFS, feed_id='A')
        dao.load_gtfs(DUMMY_GTFS, feed_id='B')

        # Check that each feed only return it's own data
        feed_a = dao.feed('A')
        self.assertTrue(feed_a.feed_id == 'A')
        feed_b = dao.feed('B')
        self.assertTrue(feed_b.feed_id == 'B')
        self.assertTrue(len(dao.agencies()) == 4)
        self.assertTrue(len(feed_a.agencies) == 2)
        self.assertTrue(len(feed_b.agencies) == 2)
        self.assertTrue(len(feed_a.routes) * 2 == len(dao.routes()))
        self.assertTrue(len(feed_b.routes) * 2 == len(dao.routes()))
        self.assertTrue(len(feed_a.stops) * 2 == len(list(dao.stops())))
        self.assertTrue(len(feed_b.stops) * 2 == len(list(dao.stops())))
        self.assertTrue(len(feed_a.calendars) * 2 == len(dao.calendars()))
        self.assertTrue(len(feed_b.calendars) * 2 == len(dao.calendars()))
        self.assertTrue(len(feed_a.trips) * 2 == len(list(dao.trips())))
        self.assertTrue(len(feed_b.trips) * 2 == len(list(dao.trips())))

    def test_complex_queries(self):
        dao = Dao(DAO_URL, sql_logging=SQL_LOG)
        dao.load_gtfs(DUMMY_GTFS)

        # Get the list of departures:
        # 1) from "Porte de Bourgogne"
        # 2) on 4th July
        # 3) between 10:00 and 14:00
        # 4) on route type BUS
        # 5) not the last of trip (only departing)
        porte_bourgogne = dao.stop("BBG")
        july4 = CalendarDate.ymd(2016, 7, 4)
        from_time = gtfstime(10, 00)
        to_time = gtfstime(14, 00)
        departures = dao.stoptimes(
                    fltr=(StopTime.stop == porte_bourgogne) & (StopTime.departure_time >= from_time) & (StopTime.departure_time <= to_time)
                    & (Route.route_type == Route.TYPE_BUS) & (func.date(CalendarDate.date) == july4.date),
                    prefetch_trips=True)

        n = 0
        for dep in departures:
            self.assertTrue(dep.stop == porte_bourgogne)
            self.assertTrue(july4 in dep.trip.calendar.dates)
            self.assertTrue(dep.trip.route.route_type == Route.TYPE_BUS)
            self.assertTrue(dep.departure_time >= from_time and dep.departure_time <= to_time)
            n += 1
        self.assertTrue(n > 10)

        # Plage is a stop that is used only in summer (hence the name!)
        plage = dao.stop("BPG")
        # Get the list of stops used by some route:
        # 1) All-year round
        route_red = dao.route("BR")
        stoplist_all = list(dao.stops(fltr=Trip.route == route_red))
        # 2) Only in january
        from_date = CalendarDate.ymd(2016, 1, 1)
        to_date = CalendarDate.ymd(2016, 1, 31)
        stoplist_jan = list(dao.stops(
                    fltr=(Trip.route == route_red) & (func.date(CalendarDate.date) >= from_date.date) & (func.date(CalendarDate.date) <= to_date.date)))
        # Now, make some tests
        self.assertTrue(len(stoplist_all) > 5)
        self.assertTrue(plage in stoplist_all)
        self.assertFalse(plage in stoplist_jan)
        stoplist = list(stoplist_all)
        stoplist.remove(plage)
        self.assertTrue(set(stoplist) == set(stoplist_jan))

        # Get all routes passing by the set of stops
        routes = dao.routes(fltr=or_(StopTime.stop == stop for stop in stoplist_jan))
        stopset = set()
        for route in routes:
            for trip in route.trips:
                for stoptime in trip.stop_times:
                    stopset.add(stoptime.stop)
        self.assertTrue(set(stoplist_jan).issubset(stopset))

    def test_custom_queries(self):
        dao = Dao(DAO_URL, sql_logging=SQL_LOG)
        dao.load_gtfs(DUMMY_GTFS)

        # A simple custom query: count the number of stops per type (stop/station)
        # SQL equivalent: SELECT stop.location_type, count(stop.location_type) FROM stop GROUP BY stop.location_type
        for type, stop_count in dao.session() \
                    .query(Stop.location_type, func.count(Stop.location_type)) \
                    .group_by(Stop.location_type) \
                   .all():
            # print("type %d : %d stops" % (type, stop_count))
            if type == Stop.TYPE_STATION:
                self.assertTrue(stop_count == 3)
            if type == Stop.TYPE_STOP:
                self.assertTrue(stop_count > 15 and stop_count < 30)

        # A more complex custom query: count the number of trips per calendar date per route on june/july
        from_date = CalendarDate.ymd(2016, 6, 1)
        to_date = CalendarDate.ymd(2016, 7, 31)
        for date, route, trip_count in dao.session() \
                    .query(CalendarDate.date, Route, func.count(Trip.trip_id)) \
                    .join(Calendar).join(Trip).join(Route) \
                    .filter((func.date(CalendarDate.date) >= from_date.date) & (func.date(CalendarDate.date) <= to_date.date)) \
                    .group_by(CalendarDate.date, Route.route_short_name) \
                    .all():
            # print("%s / %20s : %d trips" % (date, route.route_short_name + " " + route.route_long_name, trip_count))
            self.assertTrue(date >= from_date.as_date())
            self.assertTrue(date <= to_date.as_date())
            self.assertTrue(trip_count > 0)

    def test_clusterizer(self):
        dao = Dao(DAO_URL, sql_logging=SQL_LOG)
        dao.load_gtfs(DUMMY_GTFS)

        # Merge stops closer than 300m together
        sc = SpatialClusterizer(300.0)
        for stop in dao.stops():
            sc.add_point(stop)
        sc.clusterize()

        # for cluster in sc.clusters():
        #    print("---CLUSTER: %d stops" % (len(cluster)))
        #    for stop in cluster:
        #        print("%s %s" % (stop.stop_id, stop.stop_name))

        gare1 = dao.stop("GBSJT")
        gare2 = dao.stop("GBSJ")
        gare3 = dao.stop("GBSJB")
        self.assertTrue(sc.in_same_cluster(gare1, gare2))
        self.assertTrue(sc.in_same_cluster(gare1, gare3))
        self.assertTrue(sc.in_same_cluster(gare2, gare3))

        bq = dao.stop("BQ")
        bq1 = dao.stop("BQA")
        bq2 = dao.stop("BQD")
        self.assertTrue(sc.in_same_cluster(bq, bq1))
        self.assertTrue(sc.in_same_cluster(bq, bq2))

        bs = dao.stop("BS")
        bs1 = dao.stop("BS1")
        bs2 = dao.stop("BS2")
        self.assertTrue(sc.in_same_cluster(bs, bs1))
        self.assertTrue(sc.in_same_cluster(bs, bs2))

        self.assertFalse(sc.in_same_cluster(gare1, bq))
        self.assertFalse(sc.in_same_cluster(gare1, bs))
        self.assertFalse(sc.in_same_cluster(gare3, bs2))

        bjb = dao.stop("BJB")
        self.assertFalse(sc.in_same_cluster(bjb, gare1))
        self.assertFalse(sc.in_same_cluster(bjb, bs))
        self.assertFalse(sc.in_same_cluster(bjb, bq))


if __name__ == '__main__':
    unittest.main()
