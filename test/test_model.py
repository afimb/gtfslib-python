# -*- coding: utf-8 -*-
"""
@author: Laurent GRÉGOIRE <laurent.gregoire@mecatran.com>
"""

import unittest

from gtfslib.model import CalendarDate
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
            d1 = CalendarDate.ymd(2015, 12, 32)
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

if __name__ == '__main__':
    unittest.main()
