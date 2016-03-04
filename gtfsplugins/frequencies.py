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

from gtfslib.spatial import SpatialClusterizer
from gtfslib.utils import fmttime
from gtfsplugins.prettycsv import PrettyCsv
from collections import defaultdict

class Frequencies(object):
    """
    Analysis of departure frequencies for each stop (or stop cluster).
    Warning: This plugin is still in development, the interface may change.
    
    Parameters:
    --csv=<file>     Output to given file as CSV
    --cluster=<dist> Cluster stops closer than <dist> meters (default to 0)
    --dstp=<k>       Apply this penalty to clustering for stops that do not
                     share the same station (default to 0.5)
    --samename       Cluster stops only if they share the exact same name
                     (default to False).
    --alldates       To print frequencies on all filtered dates.
                     Otherwise takes date with max departures only (default).
    
    Examples:
    --filter="CalendarDate.date=='2016-01-22'"
      For all stops at a given date
    --filter="Stop.stop_name=='Villenouvelle'"
      For one stop at all dates
    --filter="(Route.route_short_name=='R1')"
      For all stops of a single route.
    """

    def __init__(self):
        pass

    def run(self, context, csv=None, cluster=0, dstp=0.5, samename=False, alldates=False, **kwargs):
        cluster_meters = float(cluster)
        dstp = float(dstp)

        print("Loading stops...")
        stops = set()
        sc = SpatialClusterizer(cluster_meters)
        for stop in context.dao().stops(fltr=context.args.filter):
            sc.add_point(stop)
            stops.add(stop)
        print("Loaded %d stops. Clusterize..." % (len(stops)))
        sc.clusterize(comparator=sc.make_comparator(samename, dstp))
        print("Aggregated in %d clusters" % (len(sc.clusters())))
        
        print("Loading calendar dates...")
        dates = set(context.dao().calendar_dates_date(fltr=context.args.filter))
        print("Loaded %d dates" % (len(dates)))
        
        print("Processing trips...")
        departures_by_clusters = defaultdict(lambda : defaultdict(list))
        ntrips = 0
        for trip in context.dao().trips(fltr=context.args.filter, prefetch_stops=True, prefetch_stop_times=True, prefetch_calendars=True):
            for stop_time in trip.stop_times:
                if not stop_time.departure_time:
                    continue
                if not stop_time.stop in stops:
                    continue
                cluster = sc.cluster_of(stop_time.stop)
                departures_by_dates = departures_by_clusters[cluster]
                for date in trip.calendar.dates:
                    if date.as_date() not in dates:
                        continue
                    departures_by_dates[date.as_date()].append(stop_time)
            if ntrips % 1000 == 0:
                print("%d trips..." % (ntrips))
            ntrips += 1

        with PrettyCsv(csv, ["cluster", "stop_id", "stop_name", "date", "departures", "min_time", "max_time", "dep_hour" ], **kwargs) as csvout:
            for cluster, departures_by_dates in departures_by_clusters.items():
                for stop in cluster.items:
                    csvout.writerow([ cluster.id, stop.stop_id, stop.stop_name ])
                if alldates:
                    # Print departure count for all dates
                    dates_to_print = list(departures_by_dates.keys())
                    dates_to_print.sort()
                else:
                    # Compute the max only
                    date_max = None
                    dep_max = 0
                    for date, departures in departures_by_dates.items():
                        ndep = len(departures)
                        if ndep >= dep_max:
                            dep_max = ndep
                            date_max = date
                    if date_max is None:
                        continue
                    dates_to_print = [ date_max ]
                for date in dates_to_print:
                    dep_times = [dep.departure_time for dep in departures_by_dates.get(date)]
                    max_hour = max(dep_times)
                    min_hour = min(dep_times)
                    delta_hour = max_hour - min_hour
                    avg_dep = float('inf') if delta_hour == 0 else len(dep_times) * 3600. / (max_hour - min_hour)
                    csvout.writerow([ cluster.id, None, None, date, len(dep_times), fmttime(min_hour), fmttime(max_hour), "%.3f" % avg_dep ])
