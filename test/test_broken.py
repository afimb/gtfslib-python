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
from sqlalchemy.orm import clear_mappers

# Location of broken.gtfs.zip.
# This unit-test is highly dependent on the CONTENT of this GTFS.
BROKEN_GTFS = "test/broken.gtfs.zip"

class TestMiniGtfs(unittest.TestCase):

    def test_broken(self):
        exception = False
        try:
            clear_mappers()
            dao = Dao("")
            dao.load_gtfs(BROKEN_GTFS, lenient=False)
        except KeyError:
            exception = True
        self.assertTrue(exception)

        clear_mappers()
        dao = Dao("")
        dao.load_gtfs(BROKEN_GTFS, lenient=True)

        # The following are based on BROKEN GTFS content,
        # that is the entities count minus broken ones.
        self.assertTrue(len(dao.routes()) == 4)
        self.assertTrue(len(list(dao.stops())) == 12)
        self.assertTrue(len(dao.calendars()) == 2)
        self.assertTrue(len(list(dao.trips())) == 104)
        self.assertTrue(len(dao.stoptimes()) == 500)
        self.assertTrue(len(dao.fare_attributes()) == 2)
        self.assertTrue(len(dao.fare_rules()) == 4)
        # This stop has missing coordinates in the broken file
        stop00 = dao.stop('FUR_CREEK_RES3')
        self.assertAlmostEquals(stop00.stop_lat, 0.0, 5)
        self.assertAlmostEquals(stop00.stop_lon, 0.0, 5)

if __name__ == '__main__':
    unittest.main()
