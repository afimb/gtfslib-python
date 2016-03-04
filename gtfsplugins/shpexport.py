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

import unicodedata
import shapefile
from gtfslib.spatial import SpatialClusterizer
from collections import defaultdict

class ShapefileExport(object):
    """
    Export data (stops, hops) to ESRI shapefile.
    Include frequency of use for each element
    * number of trips
    * number of trips x days
    Note: Usually the trips x days is a better usage metric as
    trips can be active on various number of days. If you want
    to compute the average number of trips per day, divide the
    result by the number of days (you can use date filtering).

    Parameters:
    --cluster=<dist>    Cluster stops closer than <dist> meters
    --stopshp=<file>    Output stops to given shapefile
    --hopshp=<file>     Output hops to given shapefile
    """

    def __init__(self):
        pass

    def remove_accents(self, strd):
        nfkd_form = unicodedata.normalize('NFKD', strd)
        only_ascii = nfkd_form.encode('ASCII', 'ignore')
        return only_ascii

    def run(self, context, stopshp=None, hopshp=None, cluster=0, **kwargs):
        cluster_meters = float(cluster)
        if stopshp is None and hopshp is None:
            print("Nothing to generate! Bailing out")
            return

        print("Loading stops...")
        stops = set()
        sc = SpatialClusterizer(cluster_meters)
        for stop in context.dao().stops(fltr=context.args.filter):
            sc.add_point(stop)
            stops.add(stop)
        print("Loaded %d stops. Clusterize..." % (len(stops)))
        sc.clusterize()
        print("Aggregated in %d clusters" % (len(sc.clusters())))

        print("Loading calendar dates")
        dates = set(context.dao().calendar_dates_date(fltr=context.args.filter))
        print("Loaded %d dates" % (len(dates)))

        print("Computing stop and hop trip count...")
        hop_tripcount = defaultdict(lambda: [0, 0])
        clu_tripcount = defaultdict(lambda: [0, 0])
        ntrips = 0
        for trip in context.dao().trips(fltr=context.args.filter, prefetch_stop_times=True, prefetch_stops=True, prefetch_calendars=True):
            # Compute the number of days the trip is running
            # RESTRICTED ON THE FILTERED DATES
            ndays = len([ date for date in trip.calendar.dates if date.as_date() in dates ])
            for st1, st2 in trip.hops():
                cluster1 = sc.cluster_of(st1.stop)
                cluster2 = sc.cluster_of(st2.stop)
                if cluster1 == cluster2:
                    pass
                key = (cluster1, cluster2)
                hop_tripcount[key][0] += 1
                hop_tripcount[key][1] += ndays
                clu_tripcount[cluster1][0] += 1
                clu_tripcount[cluster1][1] += ndays
            ntrips += 1
            if ntrips % 1000 == 0:
                print("%d trips..." % ntrips)

        if stopshp:
            print("Generating stops cluster shapefile...")
            stopshpwrt = shapefile.Writer(shapefile.POINT)
            stopshpwrt.field("id", "N")
            stopshpwrt.field("ids", "C", 100)
            stopshpwrt.field("name", "C", 200)
            stopshpwrt.field("ndep", "N")
            stopshpwrt.field("ndepday", "N")
            for cluster, (dep_count, depday_count) in clu_tripcount.items():
                stopshpwrt.point(cluster.lon(), cluster.lat()) # X,Y ?
                ids = cluster.aggregate(lambda s: s.stop_id, sep=';')
                names = cluster.aggregate(lambda s: s.stop_name, sep=';')
                stopshpwrt.record(cluster.id, self.remove_accents(ids),
                                  self.remove_accents(names),
                                  dep_count, depday_count)
            stopshpwrt.save(stopshp)

        if hopshp:
            print("Generating hop shapefile...")
            hopshpwrt = shapefile.Writer(shapefile.POLYLINE)
            hopshpwrt.field("from_id", "N")
            hopshpwrt.field("from_name", "C", 200)
            hopshpwrt.field("to_id", "N")
            hopshpwrt.field("to_name", "C", 200)
            hopshpwrt.field("name", "C", 200)
            hopshpwrt.field("ntrip", "N")
            hopshpwrt.field("ntripday", "N")
            for (c1, c2), (trip_count, tripday_count) in hop_tripcount.items():
                c1name = c1.aggregate(lambda s: s.stop_name, sep=';')
                c2name = c2.aggregate(lambda s: s.stop_name, sep=';')
                hopshpwrt.line(parts=[[[c1.lon(), c1.lat()], [c2.lon(), c2.lat()]]])
                hopshpwrt.record(c1.id, self.remove_accents(c1name), c2.id,
                                 self.remove_accents(c2name),
                                 self.remove_accents(c1name + " -> " + c2name),
                                 trip_count, tripday_count)
            hopshpwrt.save(hopshp)
