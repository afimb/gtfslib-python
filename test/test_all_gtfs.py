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
import hashlib
import traceback
import logging
import os
import random
import unittest
import requests

from sqlalchemy.orm import clear_mappers

from gtfslib.dao import Dao

# By default we do not enable this test, it takes ages
ENABLE = False
# Skip import of already downloaded GTFS
# Handy for re-launching the test w/o having to redo all
SKIP_EXISTING = True
# Limit loading to small GTFS only. Max size in bytes
MAX_GTFS_SIZE = 2 * 1024 * 1024
# Local cache directory
DIR = "all-gtfs.cache"
# List of ID to load. If none, download the whole list
# and process it at random.
IDS_TO_LOAD = None

# The following were known to have fancy formats that used to break:
# Contains UTF-8 BOM:
# IDS_TO_LOAD = [ 'janesville-transit-system' ]
# Contain header with space
# IDS_TO_LOAD = [ 'rseau-stan' ]
# Breaks on non-unique stop time
# IDS_TO_LOAD = [ 'biaostocka-komunikacja-miejska' ]

class TestAllGtfs(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        clear_mappers()

    # Downlaod all GTFS from GTFS data-exchange web-site
    # and load them into a DAO.
    def test_all_gtfs(self):

        if not ENABLE:
            print("This test is disabled as it is very time-consuming.")
            print("If you want to enable it, please see in the code.")
            return

        # Create temporary directory if not there
        if not os.path.isdir(DIR):
            os.mkdir(DIR)

        # Create a DAO. Re-use any existing present.
        logging.basicConfig(level=logging.INFO)
        dao = Dao("%s/all_gtfs.sqlite" % (DIR))

        deids = IDS_TO_LOAD
        if deids is None:
            print("Downloading meta-info for all agencies...")
            resource_url = "http://www.gtfs-data-exchange.com/api/agencies?format=json"
            response = requests.get(resource_url).json()
            if response.get('status_code') != 200:
                raise IOError()
            deids = []
            for entry in response.get('data'):
                deid = entry.get('dataexchange_id')
                deids.append(deid)
            # Randomize the list, otherwise we will always load ABCBus, then ...
            random.shuffle(deids)

        for deid in deids:
            try:
                local_filename = "%s/%s.gtfs.zip" % (DIR, deid)
                if os.path.exists(local_filename) and SKIP_EXISTING:
                    print("Skipping [%s], GTFS already present." % (deid))
                    continue

                print("Downloading meta-info for ID [%s]" % (deid))
                resource_url = "http://www.gtfs-data-exchange.com/api/agency?agency=%s&format=json" % deid
                response = requests.get(resource_url).json()
                status_code = response.get('status_code')
                if status_code != 200:
                    raise IOError("Error %d (%s)" % (status_code, response.get('status_txt')))
                data = response.get('data')
                agency_data = data.get('agency')
                agency_name = agency_data.get('name')
                agency_area = agency_data.get('area')
                agency_country = agency_data.get('country')

                print("Processing [%s] %s (%s / %s)" % (deid, agency_name, agency_country, agency_area))
                date_max = 0.0
                file_url = None
                file_size = 0
                file_md5 = None
                for datafile in data.get('datafiles'):
                    date_added = datafile.get('date_added')
                    if date_added > date_max:
                        date_max = date_added
                        file_url = datafile.get('file_url')
                        file_size = datafile.get('size')
                        file_md5 = datafile.get('md5sum')
                if file_url is None:
                    print("No datafile available, skipping.")
                    continue

                if file_size > MAX_GTFS_SIZE:
                    print("GTFS too large (%d bytes > max %d), skipping." % (file_size, MAX_GTFS_SIZE))
                    continue

                # Check if the file is present and do not download it.
                try:
                    existing_md5 = hashlib.md5(open(local_filename, 'rb').read()).hexdigest()
                except:
                    existing_md5 = None
                if existing_md5 == file_md5:
                    print("Using existing file '%s': MD5 checksum matches." % (local_filename))
                else:
                    print("Downloading file '%s' to '%s' (%d bytes)" % (file_url, local_filename, file_size))
                    with open(local_filename, 'wb') as local_file:
                        cnx = requests.get(file_url, stream=True)
                        for block in cnx.iter_content(1024):
                            local_file.write(block)
                    cnx.close()

                feed = dao.feed(deid)
                if feed is not None:
                    print("Removing existing data for feed [%s]" % (deid))
                    dao.delete_feed(deid)
                print("Importing into DAO as ID [%s]" % (deid))
                try:
                    dao.load_gtfs("%s/%s.gtfs.zip" % (DIR, deid), feed_id=deid)
                except:
                    error_filename = "%s/%s.error" % (DIR, deid)
                    print("Import of [%s]: FAILED. Logging error to '%s'" % (deid, error_filename))
                    with open(error_filename, 'wb') as errfile:
                        errfile.write(traceback.format_exc())
                    raise
                print("Import of [%s]: OK." % (deid))

            except Exception as error:
                logging.exception(error)
                continue

if __name__ == '__main__':
    unittest.main()
