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

from gtfslib.model import CalendarDate, Stop
import datetime


class TestModel(unittest.TestCase):

    def setUp(self):
        pass

    def test_calendar_date(self):
        self.assertEqual(True, True)
        d1 = CalendarDate.ymd(2015, 12, 31)
        d2 = CalendarDate.ymd(2016, 1, 1)
        self.assertEquals(d1.next_day(), d2)
        self.assertTrue(d1 < d2)
        self.assertTrue(d1 <= d2)
        self.assertFalse(d1 > d2)
        self.assertFalse(d1 >= d2)
        self.assertFalse(d1 == d2)
        dt = datetime.date(2015, 12, 31)
        self.assertTrue(d1 == dt)
        dates = [ CalendarDate.ymd(2016, 1, 1), CalendarDate.ymd(2016, 1, 2) ]
        self.assertTrue(CalendarDate.ymd(2016, 1, 2) in dates)

    def test_calendar_date_set(self):
        d1 = CalendarDate.ymd(2015, 12, 31)
        d2 = CalendarDate.ymd(2016, 1, 1)
        dates = set([ d1, d2 ])
        self.assertTrue(len(dates) == 2)
        d2b = CalendarDate.ymd(2016, 1, 1)
        dates.add(d2b)
        self.assertTrue(len(dates) == 2)
        d1b = CalendarDate.ymd(2015, 12, 31)
        d4 = CalendarDate.ymd(2015, 1, 2)
        dates.add(d1b)
        dates.add(d4)
        self.assertTrue(len(dates) == 3)

    def test_calendar_date_convert(self):
        d1 = CalendarDate.fromYYYYMMDD("20151231")
        d2 = CalendarDate.ymd(2015, 12, 31)
        self.assertTrue(d1 == d2)

    def test_calendar_date_out_of_range(self):
        broke = False
        try:
            d1 = CalendarDate.ymd(2015, 12, 32)  # @UnusedVariable
        except(ValueError):
            broke = True
        self.assertTrue(broke)

    def test_calendar_date_range(self):
        d1 = CalendarDate.ymd(2016, 1, 1)
        d2 = CalendarDate.ymd(2016, 2, 1)
        n = 0
        for d in CalendarDate.range(d1, d2):
            self.assertTrue(d >= d1)
            self.assertTrue(d < d2)
            n += 1
        self.assertEqual(n, 31)

    def test_same_station(self):
        s1a = Stop('F1', 'Sa', 'StopA', 45, 0)
        s1b = Stop('F1', 'Sb', 'StopB', 45, 0.1)
        s1 = Stop('F1', 'S', 'Stop', 45, 0.05, location_type=Stop.TYPE_STATION)
        s1a.parent_station_id = 'S'
        s1b.parent_station_id = 'S'
        self.assertTrue(s1a.in_same_station(s1b))
        self.assertTrue(s1b.in_same_station(s1a))
        self.assertTrue(s1.in_same_station(s1a))
        self.assertTrue(s1a.in_same_station(s1))
        s1c = Stop('F2', 'Sb', 'StopB', 45, 0.1)
        s1c.parent_station_id = 'S'
        self.assertFalse(s1c.in_same_station(s1b))
        self.assertFalse(s1c.in_same_station(s1a))
        self.assertFalse(s1a.in_same_station(s1c))

if __name__ == '__main__':
    unittest.main()
