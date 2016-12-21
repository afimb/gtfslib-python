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

from _collections import defaultdict
from sqlalchemy.sql.expression import or_
from sqlalchemy.sql.functions import func
from sqlalchemy.orm import clear_mappers

from gtfslib.dao import Dao
from gtfslib.model import CalendarDate, Stop, StopTime, Route
from gtfslib.utils import fmttime

DUMMY_GTFS = "test/dummy.gtfs.zip"
DAO_URL = ""

class TestDemo(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        clear_mappers()

    def test_demo(self):
        dao = Dao(DAO_URL, sql_logging=False)
        dao.load_gtfs(DUMMY_GTFS)

        print("List of stops named '...Bordeaux...':")
        stops_bordeaux = list(dao.stops(fltr=(Stop.stop_name.ilike('%Bordeaux%')) & (Stop.location_type == Stop.TYPE_STOP)))
        for stop in stops_bordeaux:
            print(stop.stop_name)

        print("List of routes passing by those stops:")
        routes_bordeaux = dao.routes(fltr=or_(StopTime.stop == stop for stop in stops_bordeaux))
        for route in routes_bordeaux:
            print("%s - %s" % (route.route_short_name, route.route_long_name))

        july4 = CalendarDate.ymd(2016, 7, 4)
        print("All departures from those stops on %s:" % (july4.as_date()))
        departures = list(dao.stoptimes(fltr=(or_(StopTime.stop == stop for stop in stops_bordeaux)) & (StopTime.departure_time != None) & (func.date(CalendarDate.date) == july4.date)))
        print("There is %d departures" % (len(departures)))
        for departure in departures:
            print("%30.30s %10.10s %-20.20s > %s" % (departure.stop.stop_name, fmttime(departure.departure_time), departure.trip.route.route_long_name, departure.trip.trip_headsign))

        print("Number of departures and time range per stop on %s:" % (july4.as_date()))
        departure_by_stop = defaultdict(list)
        for departure in departures:
            departure_by_stop[departure.stop].append(departure)
        for stop, deps in departure_by_stop.items():
            min_dep = min(d.departure_time for d in deps)
            max_dep = max(d.departure_time for d in deps)
            print("%30.30s %3d departures (from %s to %s)" % (stop.stop_name, len(deps), fmttime(min_dep), fmttime(max_dep)))

        # Compute the average distance and time to next stop by route type
        ntd = [ [0, 0, 0.0] for type in range(0, Route.TYPE_FUNICULAR + 1) ]
        for departure in departures:
            # The following is guaranteed to succeed as we have departure_time == Null for last stop time in trip
            next_arrival = departure.trip.stop_times[departure.stop_sequence + 1]
            hop_dist = next_arrival.shape_dist_traveled - departure.shape_dist_traveled
            hop_time = next_arrival.arrival_time - departure.departure_time
            route_type = departure.trip.route.route_type
            ntd[route_type][0] += 1
            ntd[route_type][1] += hop_time
            ntd[route_type][2] += hop_dist
        for route_type in range(0, len(ntd)):
            n, t, d = ntd[route_type]
            if n > 0:
                print("The average distance to the next stop on those departures for route type %d is %.2f meters" % (route_type, d / n))
                print("The average time in sec to the next stop on those departures for route type %d is %s" % (route_type, fmttime(t / n)))

if __name__ == '__main__':
    unittest.main()
