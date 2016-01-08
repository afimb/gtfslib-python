# -*- coding: utf-8 -*-
"""gtfsdbloader - GTFS to GTFS' conversion tool and database loader

Usage:
  gtfsdbloader <database> (--load=<gtfs> | --delete | --list) [--id=<id>] [--append] [--logsql]
  gtfsdbloader (-h | --help)
  gtfsdbloader --version

Options:
  <database>           The database to use. If a file, assume SQLite.
                       For PostgreSQL: "postgresql://user:pwd@host:port/db".
  --load=<gtfs>        The zipped GTFS file to load.
  --append             Do not delete existing feed when loading (TODO).
  --delete             Delete feed.
  --list               List all feeds.
  --id=<id>            Set the feed ID in case multiple GTFS are to be loaded.
  -h --help            Show help on options.
  --version            Show lib / program version.
  --logsql             Enable SQL logging (very verbose)

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


def main():
    arguments = docopt(__doc__, version='gtfsdbloader 0.1')
    if arguments['--id'] is None:
        arguments['--id'] = ""

    # TODO Configure logging properly?
    logger = logging.getLogger('libgtfs')
    logger.setLevel(logging.INFO)
    logger.addHandler(StreamHandler(sys.stdout))

    dao = Dao(arguments['<database>'], sql_logging=arguments['--logsql'])

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
        dao.load_gtfs(arguments['--load'], feed_id=arguments['--id'])

if __name__ == '__main__':
    main()