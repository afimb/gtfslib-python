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

import six
import logging
import argparse

from gtfsplugins.demoplugin import DemoPlugin
from gtfsplugins.decret_2015_1610 import Decret_2015_1610
from gtfsplugins.frequencies import Frequencies
from gtfsplugins.tripsperday import TripsPerDay
from gtfsplugins.shpexport import ShapefileExport
from gtfsplugins.export import GtfsExport

# Please keep the following unused imports, they are used by the --filter eval.
from gtfslib.dao import Dao
from gtfslib.model import FeedInfo, Agency, Route, Zone, Stop, Calendar, CalendarDate, Trip, StopTime, Shape, ShapePoint, FareAttribute, FareRule  # @UnusedImport
from gtfslib.spatial import RectangularArea  # @UnusedImport

# TODO Dynamically scan packages
PLUGINS = [ DemoPlugin, Decret_2015_1610, Frequencies, TripsPerDay, ShapefileExport, GtfsExport ]

class PluginContext(object):
    """The class given as execution context to a plugin.
    Propose helper methods to filter objects, or get the DAO."""

    def __init__(self, dao, args):
        self._dao = dao
        self.args = args

    def dao(self):
        return self._dao

def main():

    parser = argparse.ArgumentParser(description='GTFS plugin runner', epilog="Copyright (c) 2016 AFIMB & Mecatran")
    parser.add_argument("database", nargs='?', help="Database to load data from")
    parser.add_argument("plugin", nargs='?', help="Name of plugin to run")
    parser.add_argument('-l', '--list', help="List all available plugins", action="store_true")
    parser.add_argument('--filter', help="Specify object filter. Examples: --filter=\"Stop.stop_name=='FooBar'\",  --filter=\"(Route.route_type.in_([Route.TYPE_SUBWAY, Route.TYPE_TRAM])\",  --filter=\"CalendarDate.date=='2016-02-22'\"", type=str)
    parser.add_argument('--logsql', help="Enable SQL logging (very verbose)", action="store_true")
    parser.add_argument('--schema', help="Set the schema to use (for PostgreSQL).", type=str)

    args, xargs = parser.parse_known_args()

    # Extract extra arguments, to give them to the plugin
    kwargs = {}
    for xarg in xargs:
        kv = xarg.split('=', 1)
        if len(kv) != 1 and len(kv) != 2 or not kv[0].startswith('--'):
            print("Invalid extra argument: %s, use '--param=value' (or '--param' for boolean flag)" % (xarg))
            continue
        kwargs[kv[0][2:]] = kv[1] if len(kv) == 2 else True

    # List plugins
    if args.list:
        print("List of all available plugins:")
        print("")
        for plugin in PLUGINS:
            if plugin.__doc__:
                print("%s:" % plugin.__name__)
                print(plugin.__doc__)
        exit(0)

    # Lookup for plugin
    try:
        plugin_class = six.next(p for p in PLUGINS if p.__name__ == args.plugin)
    except:
        print("Plugin not found: %s" % args.plugin)
        exit(1)

    dao = Dao(args.database, sql_logging=args.logsql, schema=args.schema)

    def _evaluate(strarg, dao):
        return None if strarg is None else eval(strarg, globals(), locals())
    args.filter = _evaluate(args.filter, dao)

    # TODO Configure logging
    logging.basicConfig(level=logging.INFO)

    context = PluginContext(dao, args)

    # Instantiate and run the plugin
    plugin = plugin_class()
    retval = plugin.run(context, **kwargs)

    # Convert the return value to something digestable by scripts
    if isinstance(retval, int):
        exit(retval)
    else:
        exit(1 if retval else 0)

if __name__ == '__main__':
    main()
