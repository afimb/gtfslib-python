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

# Location of mini.gtfs.zip.
# This unit-test is highly dependent on the CONTENT of this GTFS.
MINI_GTFS = "test/mini.gtfs.zip"

DAO_URL = ""
# To unit-test with postgresql, create a db "gtfs" with user "gtfs" and uncomment the following line:
# DAO_URL = "postgresql://gtfs@localhost/gtfs"
# Set this to true to activate SQL logging
SQL_LOG = False

class TestMiniGtfs(unittest.TestCase):

    def test_gtfs_data(self):
        dao = Dao(DAO_URL, sql_logging=SQL_LOG)
        dao.load_gtfs(MINI_GTFS)

        # Check feed
        feed = dao.feed()
        self.assertTrue(feed.feed_id == "")
        self.assertTrue(len(dao.agencies()) == 1)
        self.assertTrue(len(dao.routes()) == 1)
        self.assertTrue(len(feed.agencies) == 1)
        self.assertTrue(len(feed.routes) == 1)

        # Check if optional route agency is set
        a = dao.agency("A")
        self.assertTrue(a.agency_name == "Mini Agency")
        self.assertTrue(len(a.routes) == 1)

if __name__ == '__main__':
    unittest.main()
