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

"""gtfsdbloader - GTFS to GTFS' conversion tool and database loader

Usage:
  gtfsdbloader <database> (--load=<gtfs> | --delete | --list) [--id=<id>]
                        [--logsql] [--lenient] [--schema=<schema>]
                        [--disablenormalize]
  gtfsdbloader (-h | --help)
  gtfsdbloader --version

Options:
  <database>           The database to use. If a file, assume SQLite.
                       For PostgreSQL: "postgresql://user:pwd@host:port/db".
  --load=<gtfs>        The zipped GTFS file to load.
  --delete             Delete feed.
  --list               List all feeds.
  --id=<id>            Set the feed ID in case multiple GTFS are to be loaded.
  -h --help            Show help on options.
  --version            Show lib / program version.
  --logsql             Enable SQL logging (very verbose)
  --lenient            Allow some level of brokenness in GTFS input.
  --schema=<schema>    Set the schema to use (for PostgreSQL).
  --disablenormalize   Disable shape and stop times normalization. Be careful
                       if you use this option, as missing stop times will not
                       be interpolated, and shape_dist_traveled will not be
                       computed or converted to meters.

Examples:
  gtfsdbloader db.sqlite --load=sncf.zip --id=sncf
        Load the GTFS sncf.zip into db.sqlite using id "sncf",
        deleting previous data.
  gtfsdbloader db.sqlite --delete --id=moontransit
        Delete the "moontransit" feed from the database.
  gtfsdbloader db.sqlite --list
        List all feed IDs from db.sqlite
  gtfsdbloader postgresql://gtfs@localhost/gtfs --load gtfs.zip
        Load gtfs.zip into a postgresql database,
        using a default (empty) feed ID.

Authors:
  CEREMA / AFIMB
  Laurent GRÉGOIRE (MECATRAN) <laurent.gregoire@mecatran.com>
"""
from docopt import docopt
from logging import StreamHandler
import logging
import sys
from gtfslib.dao import Dao
import gtfslib

def main():
    arguments = docopt(__doc__, version='gtfsdbloader %s' % gtfslib.__version__)
    if arguments['--id'] is None:
        arguments['--id'] = ""

    # TODO Configure logging properly?
    logger = logging.getLogger('libgtfs')
    logger.setLevel(logging.INFO)
    logger.addHandler(StreamHandler(sys.stdout))

    dao = Dao(arguments['<database>'],
              sql_logging=arguments['--logsql'],
              schema=arguments['--schema'])

    if arguments['--list']:
        for feed in dao.feeds():
            print(feed.feed_id if feed.feed_id != "" else "(default)")

    if arguments['--delete'] or arguments['--load']:
        feed_id = arguments['--id']
        existing_feed = dao.feed(feed_id)
        if existing_feed:
            logger.warn("Deleting existing feed ID '%s'" % feed_id)
            dao.delete_feed(feed_id)
            dao.commit()

    if arguments['--load']:
        dao.load_gtfs(arguments['--load'],
                      feed_id=arguments['--id'],
                      lenient=arguments['--lenient'],
                      disable_normalization=arguments['--disablenormalize'])

if __name__ == '__main__':
    main()