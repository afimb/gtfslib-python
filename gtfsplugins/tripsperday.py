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

from gtfsplugins.prettycsv import PrettyCsv
from collections import defaultdict

class TripsPerDay(object):
    """
    Compute the number of trips per route per day.

    Parameters:
    --csv=<file>    Output to given file as CSV
    --maxwidth=<n>  Max column width of console output
    --byagency      Aggregate by agency
    --byroute       Aggregate by route
    --bydir         Aggregate by route and direction

    Examples:
    --filter="(CalendarDate.date >= '2016-01-01') &
              (CalendarDate.date <= '2016-01-31')"
      Restrict to some date range
    --filter="(Route.route_short_name=='R1')"
      Restrict to route R1
    """

    def __init__(self):
        pass

    def run(self, context, csv=None, byagency=False, byroute=False, bydir=False, **kwargs):

        print("Loading calendar dates...")
        dates = set(context.dao().calendar_dates_date(fltr=context.args.filter))
        print("Loaded %d dates" % (len(dates)))

        print("Processing trips...")
        tripcount = defaultdict(lambda: defaultdict(int))
        keys = set()
        ntrips = 0
        for trip in context.dao().trips(fltr=context.args.filter, prefetch_stops=False, prefetch_stop_times=False, prefetch_calendars=True, prefetch_routes=True):
            if byagency:
                key = (trip.route.agency.agency_name, trip.route.agency)
            elif byroute:
                key = (trip.route.name(), trip.route)
            elif bydir:
                key = ("%s-%d" % (trip.route.name(), trip.direction_id), (trip.direction_id, trip.route))
            else:
                key = ("SUM", None)
            keys.add(key)
            for date in trip.calendar.dates:
                if date.as_date() not in dates:
                    continue
                tripcount[date.as_date()][key] += 1
            if ntrips % 1000 == 0:
                print("%d trips..." % (ntrips))
            ntrips += 1
        print("Processed %d trips" % (ntrips))

        keys = list(keys)
        keys.sort(key=lambda k: k[0])
        dates = list(tripcount.keys())
        dates.sort()

        with PrettyCsv(csv, ["date"] + [ key[0] for key in keys ], **kwargs) as csvout:
            for date in dates:
                row = { "date" : date }
                tkc = tripcount.get(date)
                for key in keys:
                    count = tkc.get(key, 0)
                    if count > 0:
                        row[key[0]] = count
                csvout.writerow(row)
