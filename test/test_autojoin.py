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

import re
import unittest

from sqlalchemy.orm import clear_mappers

from gtfslib.dao import _AutoJoiner, Dao
from gtfslib.model import CalendarDate, FeedInfo, Agency, Route, Calendar, Stop, \
    Trip, StopTime, Transfer, Shape, ShapePoint, Zone, FareAttribute, FareRule


class TestAutoJoin(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        clear_mappers()

    def test_autojoin(self):
        dao = Dao()

        query = _AutoJoiner(dao._orm, dao.session().query(Agency), Stop.stop_name == 'FOOBAR').autojoin()
        self._check(query, ['routes', 'trips', 'stop_times', 'stops'])
        query = _AutoJoiner(dao._orm, dao.session().query(Agency), CalendarDate.date == '2016-01-01').autojoin()
        self._check(query, ['routes', 'trips', 'calendar', 'calendar_dates'])
        query = _AutoJoiner(dao._orm, dao.session().query(CalendarDate), Stop.stop_name == 'FOOBAR').autojoin()
        self._check(query, ['calendar', 'trips', 'stop_times', 'stops'])
        query = _AutoJoiner(dao._orm, dao.session().query(CalendarDate), Agency.agency_name == 'FOOBAR').autojoin()
        self._check(query, ['calendar', 'trips', 'routes', 'agency'])
        query = _AutoJoiner(dao._orm, dao.session().query(Stop), CalendarDate.date == '2016-01-01').autojoin()
        self._check(query, ['stop_times', 'trips', 'calendar', 'calendar_dates'])
        query = _AutoJoiner(dao._orm, dao.session().query(Stop), Agency.agency_name == 'FOOBAR').autojoin()
        self._check(query, ['stop_times', 'trips', 'routes', 'agency'])

        query = _AutoJoiner(dao._orm, dao.session().query(Agency), (Stop.stop_name == 'FOOBAR') & (CalendarDate.date == '2016-01-01')).autojoin()
        self._check(query, ['routes', 'trips', 'calendar', 'calendar_dates', 'stop_times', 'stops'])

        query = _AutoJoiner(dao._orm, dao.session().query(Trip), (Route.route_long_name == 'FOOBAR') & (StopTime.departure_time > 2000) & (CalendarDate.date == '2016-01-01')).autojoin()
        self._check(query, ['calendar', 'calendar_dates', 'routes', 'stop_times'])

        query = _AutoJoiner(dao._orm, dao.session().query(Trip), Agency.agency_name == 'FOOBAR').autojoin()
        self._check(query, ['routes', 'agency'])
        query = _AutoJoiner(dao._orm, dao.session().query(Trip), Stop.stop_name == 'FOOBAR').autojoin()
        self._check(query, ['stop_times', 'stops'])
        query = _AutoJoiner(dao._orm, dao.session().query(Trip), CalendarDate.date == '2016-01-01').autojoin()
        self._check(query, ['calendar', 'calendar_dates'])
        query = _AutoJoiner(dao._orm, dao.session().query(Route), Agency.agency_name == 'FOOBAR').autojoin()
        self._check(query, ['agency'])
        query = _AutoJoiner(dao._orm, dao.session().query(Route), Stop.stop_name == 'FOOBAR').autojoin()
        self._check(query, ['trips', 'stop_times', 'stops'])

        query = _AutoJoiner(dao._orm, dao.session().query(Shape), Agency.agency_name == 'FOOBAR').autojoin()
        self._check(query, ['trips', 'routes', 'agency'])

        query = _AutoJoiner(dao._orm, dao.session().query(FareAttribute), FareRule.contains_id == 'Z1').autojoin()
        self._check(query, ['fare_rules'])

    def _check(self, query, joins):
        query_joins = re.findall("JOIN\s+([a-z_]+)", str(query))
        # print(query_joins)
        self.assertTrue(joins == query_joins)

if __name__ == '__main__':
    unittest.main()
