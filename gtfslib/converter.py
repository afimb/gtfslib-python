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
import logging

from gtfslib.model import Agency, FeedInfo, Route, Calendar, CalendarDate, Stop, \
    Trip, StopTime, Transfer, Shape, ShapePoint, Zone, FareAttribute, FareRule
from gtfslib.spatial import DistanceCache, orthodromic_distance,\
    orthodromic_seg_distance
from gtfslib.utils import timing, fmttime, ContinousPiecewiseLinearFunc

logger = logging.getLogger('libgtfs')

DOW_NAMES = { 0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday', 4: 'friday', 5: 'saturday', 6: 'sunday' }

def _toint(s, default_value=None):
    if s is None or len(s) == 0:
        if default_value is None:
            raise ValueError()
        return default_value
    return int(s)

def _timetoint(s, default_value=None):
    if s is None or len(s) == 0:
        if default_value is None:
            raise ValueError()
        return default_value
    hms = s.split(':')
    if len(hms) != 3:
        raise ValueError("Invalid date/time: %s" % s)
    return int(hms[0]) * 3600 + int(hms[1]) * 60 + int(hms[2])

def _tofloat(s, default_value=None):
    if s is None or len(s) == 0:
        return default_value
    return float(s)

def _todate(s, default_value=None):
    if s is None or len(s) == 0:
        return default_value
    return CalendarDate.fromYYYYMMDD(s).as_date()

class _CacheEntry(object):

    def __init__(self, distance):
        self._distance = distance
        self._next_entries = {}

    def next_entry(self, stop):
        return self._next_entries.get(stop.stop_id)

    def distance(self):
        return self._distance

    def insert(self, stop, distance):
        next_entry = _CacheEntry(distance)
        self._next_entries[stop.stop_id] = next_entry
        return next_entry

class _OdometerShape(object):

    # A 0.1% cone - Coefficient to defavor points further away on a shape
    # when doing stop snapping to shape. The summit angle of the offset cone
    # is 2 * arctan(K).
    K = 0.001

    def __init__(self, shape):
        self._shape = shape
        self._cache = _CacheEntry(None)
        self._cache_hit = 0
        self._cache_miss = 0
        if all(pt.shape_dist_traveled != -999999 for pt in shape.points):
            self._xdist = ContinousPiecewiseLinearFunc()
        else:
            self._xdist = None
        # Normalize the shape here:
        # 1) dist_traveled to meters
        # 2) pt_seq to contiguous numbering from 0
        ptseq = 0
        distance_meters = 0.0
        last_pt = None
        shape.points.sort(key=lambda p: p.shape_pt_sequence)
        for pt in shape.points:
            if last_pt is not None:
                # Note: we do not use distance cache, as most probably
                # many of the points will be different from each other.
                distance_meters += orthodromic_distance(last_pt, pt)
            last_pt = pt
            pt.shape_pt_sequence = ptseq
            old_distance = pt.shape_dist_traveled
            pt.shape_dist_traveled = distance_meters
            # Remember the distance mapping for stop times
            if self._xdist:
                self._xdist.append(old_distance, pt.shape_dist_traveled)
            ptseq += 1

    def reset(self):
        self._distance = 0
        self._istart = 0
        self._cache_cursor = self._cache

    def dist_traveled(self, stop, old_dist_traveled):
        if old_dist_traveled and self._xdist:
            # Case 1: we have in the original data shape_dist_traveled
            # We need to remap from the old scale to the new meter scale
            return self._xdist.interpolate(old_dist_traveled)
        else:
            # Case 2: we do not have original shape_dist_traveled
            # We need to determine ourselves where in the shape we lie
            # TODO Implement a cache, this can be slow for lots of trips
            # and the result is the same for the same pattern
            # Check the cache first
            cache_entry = self._cache_cursor.next_entry(stop)
            if cache_entry is not None:
                self._cache_cursor = cache_entry
                self._cache_hit += 1
                return cache_entry.distance()
            min_dist = 1e20
            best_i = self._istart
            best_dist = 0
            for i in range(self._istart, len(self._shape.points) - 1):
                a = self._shape.points[i]
                b = self._shape.points[i+1]
                dist, pdist = orthodromic_seg_distance(stop, a, b)
                newdist = a.shape_dist_traveled + pdist
                howfar = newdist - self._distance
                # Add a slight "cone" offset. There are pathological
                # cases with backtracking shapes where the best distance
                # is slightly better way further (for eg 0.01m) than at
                # the starting point (for eg 0.02m). In that case we should
                # obviously keep the first point instead of moving too fast
                # to the shape end. That offset should help for some cases.
                dist += howfar * self.K
                if dist < min_dist:
                    min_dist = dist
                    best_i = i
                    best_dist = newdist
            if best_dist > self._distance:
                self._distance = best_dist
            else:
                delta = self._distance - best_dist
                if delta > 10:
                    # This is harmless if the backtracking distance is small.
                    # We have lots of false positive (<<1m) due to rounding errors.
                    logger.warn("Backtracking of %f m detected in shape %s for stop %s (%s) (%f,%f) at distance %f < %f m on segment #[%d-%d]" % (
                                delta, self._shape.shape_id, stop.stop_id, stop.stop_name, stop.stop_lat, stop.stop_lon, best_dist, self._distance, best_i, best_i+1))
            self._istart = best_i
            self._cache_miss += 1
            self._cache_cursor = self._cache_cursor.insert(stop, self._distance)
            return self._distance

    def _debug_cache(self):
        logger.debug("Shape %s: Cache hit: %d, misses: %d" % (self._shape.shape_id, self._cache_hit, self._cache_miss))

class _Odometer(object):
    _odoshp = None
    _dcache = None

    def normalize_and_register_shape(self, shape):
        self._odoshp = _OdometerShape(shape)
        self.reset()

    def register_noshape(self):
        self._odoshp = None
        self.reset()

    def reset(self):
        if self._odoshp is not None:
            self._odoshp.reset()
        self._distance = 0
        self._last_stop = None
        self._dcache = DistanceCache()

    def dist_traveled(self, stop, old_dist_traveled):
        if self._odoshp is not None:
            # We have a shape, use it
            return self._odoshp.dist_traveled(stop, old_dist_traveled)
        # We do not have shape, use straight-line distance between
        # consecutive stops
        if self._last_stop is not None:
            self._distance += self._dcache.orthodromic_distance(self._last_stop, stop)
        self._last_stop = stop
        return self._distance

    def _debug_cache(self):
        self._odoshp._debug_cache()

@timing
def _convert_gtfs_model(feed_id, gtfs, dao, lenient=False, disable_normalization=False):
    
    feedinfo2 = None
    logger.info("Importing feed ID '%s'" % feed_id)
    n_feedinfo = 0
    for feedinfo in gtfs.feedinfo():
        n_feedinfo += 1
        if n_feedinfo > 1:
            logger.error("Feed info should be unique if defined. Taking first one." % (n_feedinfo))
            break
        # TODO Automatically compute from calendar range if missing?
        feedinfo['feed_start_date'] = _todate(feedinfo.get('feed_start_date'))
        feedinfo['feed_end_date'] = _todate(feedinfo.get('feed_end_date'))
        feedinfo2 = FeedInfo(feed_id, **feedinfo)
    if feedinfo2 is None:
        # Optional, generate empty feed info
        feedinfo2 = FeedInfo(feed_id)
    dao.add(feedinfo2)
    dao.flush()
    logger.info("Imported %d feedinfo" % n_feedinfo)

    logger.info("Importing agencies...")
    n_agencies = 0
    single_agency = None
    agency_ids = set()
    for agency in gtfs.agencies():
        # agency_id is optional only if we have a single agency
        if n_agencies == 0 and agency.get('agency_id') is None:
            agency['agency_id'] = ''
        agency2 = Agency(feed_id, **agency)
        if n_agencies == 0:
            single_agency = agency2
        else:
            single_agency = None
        n_agencies += 1
        dao.add(agency2)
        agency_ids.add(agency2.agency_id)
    dao.flush()
    logger.info("Imported %d agencies" % n_agencies)

    def import_stop(stop, stoptype, zone_ids, item_ids, station_ids=None):
        zone_id = stop.get('zone_id')
        if zone_id and zone_id not in zone_ids:
            # Lazy-creation of zone
            zone = Zone(feed_id, zone_id)
            zone_ids.add(zone_id)
            dao.add(zone)
        stop['location_type'] = _toint(stop.get('location_type'), Stop.TYPE_STOP)
        if stop['location_type'] != stoptype:
            return 0
        stop['wheelchair_boarding'] = _toint(stop.get('wheelchair_boarding'), Stop.WHEELCHAIR_UNKNOWN)
        lat = _tofloat(stop.get('stop_lat'), None)
        lon = _tofloat(stop.get('stop_lon'), None)
        if lat is None or lon is None:
            if lenient:
                logger.error("Missing lat/lon for '%s', set to default (0,0)" % (stop,))
                if lat is None:
                    lat = 0
                if lon is None:
                    lon = 0
            else:
                raise ValueError("Missing mandatory lat/lon for '%s'." % (stop,))
        stop['stop_lat'] = lat
        stop['stop_lon'] = lon
        # This field has been renamed for consistency
        parent_id = stop.get('parent_station')
        stop['parent_station_id'] = parent_id if parent_id else None
        if parent_id and station_ids and parent_id not in station_ids:
            if lenient:
                logger.error("Parent station ID '%s' in '%s' is invalid, resetting." % (parent_id, stop))
                stop['parent_station_id'] = None
            else:
                raise KeyError("Parent station ID '%s' in '%s' is invalid." % (parent_id, stop))
        stop.pop('parent_station', None)
        stop2 = Stop(feed_id, **stop)
        dao.add(stop2)
        item_ids.add(stop2.stop_id)
        return 1

    stop_ids = set()
    station_ids = set()
    zone_ids = set()
    logger.info("Importing zones, stations and stops...")
    n_stations = n_stops = 0
    for station in gtfs.stops():
        n_stations += import_stop(station, Stop.TYPE_STATION, zone_ids, station_ids)
    for stop in gtfs.stops():
        n_stops += import_stop(stop, Stop.TYPE_STOP, zone_ids, stop_ids, station_ids)
    dao.flush()
    logger.info("Imported %d zones, %d stations and %d stops" % (len(zone_ids), n_stations, n_stops))

    logger.info("Importing transfers...")
    n_transfers = 0
    for transfer in gtfs.transfers():
        from_stop_id = transfer.get('from_stop_id')
        to_stop_id = transfer.get('to_stop_id')
        transfer['transfer_type'] = _toint(transfer.get('transfer_type'), 0)
        for stop_id in (from_stop_id, to_stop_id):
            if stop_id not in station_ids and stop_id not in stop_ids:
                if lenient:
                    logger.error("Stop ID '%s' in '%s' is invalid, skipping." % (stop_id, transfer))
                    continue
                else:
                    raise KeyError("Stop ID '%s' in '%s' is invalid." % (stop_id, transfer))
        transfer2 = Transfer(feed_id, **transfer)
        n_transfers += 1
        dao.add(transfer2)
    dao.flush()
    logger.info("Imported %d transfers" % (n_transfers))
    
    logger.info("Importing routes...")
    n_routes = 0
    route_ids = set()
    for route in gtfs.routes():
        route['route_type'] = int(route.get('route_type'))
        agency_id = route.get('agency_id')
        if (agency_id is None or len(agency_id) == 0) and single_agency is not None:
            # Route.agency is optional if only a single agency exists.
            agency_id = route['agency_id'] = single_agency.agency_id
        if agency_id not in agency_ids:
            if lenient:
                logger.error("Agency ID '%s' in '%s' is invalid, skipping route." % (agency_id, route))
                continue
            else:
                raise KeyError("agency ID '%s' in '%s' is invalid." % (agency_id, route))
        route2 = Route(feed_id, **route)
        dao.add(route2)
        route_ids.add(route2.route_id)
        n_routes += 1
    dao.flush()
    logger.info("Imported %d routes" % n_routes)

    logger.info("Importing fares...")
    n_fares = 0
    for fare_attr in gtfs.fare_attributes():
        fare_id = fare_attr.get('fare_id')
        fare_price = _tofloat(fare_attr.get('price'))
        currency_type = fare_attr.get('currency_type')
        payment_method = _toint(fare_attr.get('payment_method'))
        n_transfers = None
        if fare_attr.get('transfers') is not None:
            n_transfers = _toint(fare_attr.get('transfers'))
        transfer_duration = None
        if fare_attr.get('transfer_duration') is not None:
            transfer_duration = _toint(fare_attr.get('transfer_duration'))
        fare = FareAttribute(feed_id, fare_id, fare_price, currency_type,
                             payment_method, n_transfers, transfer_duration)
        dao.add(fare)
        n_fares += 1
    dao.flush()
    fare_rules = set()
    for fare_rule in gtfs.fare_rules():
        fare_rule2 = FareRule(feed_id, **fare_rule)
        if fare_rule2 in fare_rules:
            if lenient:
                logger.error("Duplicated fare rule (%s), skipping." % (fare_rule2))
                continue
            else:
                raise KeyError("Duplicated fare rule (%s)" % (fare_rule2))
        dao.add(fare_rule2)
        fare_rules.add(fare_rule2)
    dao.flush()
    logger.info("Imported %d fare and %d rules" % (n_fares, len(fare_rules)))

    logger.info("Importing calendars...")
    calanddates2 = {}
    for calendar in gtfs.calendars():
        calid = calendar.get('service_id')
        calendar2 = Calendar(feed_id, calid)
        dates2 = []
        start_date = CalendarDate.fromYYYYMMDD(calendar.get('start_date'))
        end_date = CalendarDate.fromYYYYMMDD(calendar.get('end_date'))
        for d in CalendarDate.range(start_date, end_date.next_day()):
            if int(calendar.get(DOW_NAMES[d.dow()])):
                dates2.append(d)
        calanddates2[calid] = (calendar2, set(dates2))

    logger.info("Normalizing calendar dates...")
    for caldate in gtfs.calendar_dates():
        calid = caldate.get('service_id')
        date2 = CalendarDate.fromYYYYMMDD(caldate.get('date'))
        addremove = int(caldate.get('exception_type'))
        if calid in calanddates2:
            calendar2, dates2 = calanddates2[calid]
        else:
            calendar2 = Calendar(feed_id, calid)
            dates2 = set([])
            calanddates2[calid] = (calendar2, dates2)
        if addremove == 1:
            dates2.add(date2)
        elif addremove == 2:
            if date2 in dates2:
                dates2.remove(date2)
    n_calendars = 0
    n_caldates = 0
    calendar_ids = set()
    for (calendar2, dates2) in calanddates2.values():
        calendar2.dates = [ d for d in dates2 ]
        dao.add(calendar2)
        calendar_ids.add(calendar2.service_id)
        n_calendars += 1
        n_caldates += len(calendar2.dates)
    dao.flush()
    logger.info("Imported %d calendars and %d dates" % (n_calendars, n_caldates))

    logger.info("Importing shapes...")
    n_shape_pts = 0
    shape_ids = set()
    shapepts_q = []
    for shpt in gtfs.shapes():
        shape_id = shpt.get('shape_id')
        if shape_id not in shape_ids:
            dao.add(Shape(feed_id, shape_id))
            dao.flush()
            shape_ids.add(shape_id)
        pt_seq = _toint(shpt.get('shape_pt_sequence'))
        # This field is optional
        dist_traveled = _tofloat(shpt.get('shape_dist_traveled'), -999999)
        lat = _tofloat(shpt.get('shape_pt_lat'))
        lon = _tofloat(shpt.get('shape_pt_lon'))
        shape_point = ShapePoint(feed_id, shape_id, pt_seq, lat, lon, dist_traveled)
        shapepts_q.append(shape_point)
        n_shape_pts += 1
        if n_shape_pts % 100000 == 0:
            logger.info("%d shape points" % n_shape_pts)
            dao.bulk_save_objects(shapepts_q)
            dao.flush()
            shapepts_q = []
    dao.bulk_save_objects(shapepts_q)
    dao.flush()
    logger.info("Imported %d shapes and %d points" % (len(shape_ids), n_shape_pts))

    logger.info("Importing trips...")
    n_trips = 0
    trips_q = []
    trip_ids = set()
    for trip in gtfs.trips():
        trip['wheelchair_accessible'] = _toint(trip.get('wheelchair_accessible'), Trip.WHEELCHAIR_UNKNOWN)
        trip['bikes_allowed'] = _toint(trip.get('bikes_allowed'), Trip.BIKES_UNKNOWN)
        cal_id = trip.get('service_id')
        if cal_id not in calendar_ids:
            if lenient:
                logger.error("Calendar ID '%s' in '%s' is invalid. Skipping trip." % (cal_id, trip))
                continue
            else:
                raise KeyError("Calendar ID '%s' in '%s' is invalid." % (cal_id, trip))
        route_id = trip.get('route_id')
        if route_id not in route_ids:
            if lenient:
                logger.error("Route ID '%s' in '%s' is invalid. Skipping trip." % (route_id, trip))
                continue
            else:
                raise KeyError("Route ID '%s' in trip '%s' is invalid." % (route_id, trip))
        trip2 = Trip(feed_id, frequency_generated=False, **trip)
        
        trips_q.append(trip2)
        n_trips += 1
        if n_trips % 10000 == 0:
            dao.bulk_save_objects(trips_q)
            dao.flush()
            logger.info('%s trips' % n_trips)
            trips_q = []

        trip_ids.add(trip.get('trip_id'))
    dao.bulk_save_objects(trips_q)
    dao.flush()
    
    logger.info("Imported %d trips" % n_trips)

    logger.info("Importing stop times...")
    n_stoptimes = 0
    stoptimes_q = []
    for stoptime in gtfs.stop_times():
        stopseq = _toint(stoptime.get('stop_sequence'))
        # Mark times to interpolate later on 
        arrtime = _timetoint(stoptime.get('arrival_time'), -999999)
        deptime = _timetoint(stoptime.get('departure_time'), -999999)
        if arrtime == -999999:
            arrtime = deptime
        if deptime == -999999:
            deptime = arrtime
        interp = arrtime < 0 and deptime < 0
        shpdist = _tofloat(stoptime.get('shape_dist_traveled'), -999999)
        pkptype = _toint(stoptime.get('pickup_type'), StopTime.PICKUP_DROPOFF_REGULAR)
        drptype = _toint(stoptime.get('drop_off_type'), StopTime.PICKUP_DROPOFF_REGULAR)
        trip_id = stoptime.get('trip_id')
        if trip_id not in trip_ids:
            if lenient:
                logger.error("Trip ID '%s' in '%s' is invalid. Skipping stop time." % (trip_id, stoptime))
                continue
            else:
                raise KeyError("Trip ID '%s' in '%s' is invalid." % (trip_id, stoptime))
        stop_id = stoptime.get('stop_id')
        if stop_id not in stop_ids:
            if lenient:
                logger.error("Stop ID '%s' in '%s' is invalid. Skipping stop time." % (stop_id, stoptime))
                continue
            else:
                raise KeyError("Trip ID '%s' in stoptime '%s' is invalid." % (stop_id, stoptime))
        stoptime2 = StopTime(feed_id, trip_id, stop_id,
                stop_sequence=stopseq, arrival_time=arrtime, departure_time=deptime,
                shape_dist_traveled=shpdist, interpolated=interp,
                pickup_type=pkptype, drop_off_type=drptype,
                stop_headsign=stoptime.get('stop_headsign'))
        stoptimes_q.append(stoptime2)
        n_stoptimes += 1
        # Commit every now and then
        if n_stoptimes % 50000 == 0:
            logger.info("%d stop times" % n_stoptimes)
            dao.bulk_save_objects(stoptimes_q)
            dao.flush()
            stoptimes_q = []
    dao.bulk_save_objects(stoptimes_q)

    logger.info("Imported %d stop times" % n_stoptimes)
    logger.info("Committing")
    dao.flush()
    # TODO Add option to enable/disable this commit
    # to ensure import is transactionnal
    dao.commit()
    logger.info("Commit done")

    def normalize_trip(trip, odometer):
        stopseq = 0
        n_stoptimes = len(trip.stop_times)
        last_stoptime_with_time = None
        to_interpolate = []
        odometer.reset()
        for stoptime in trip.stop_times:
            stoptime.stop_sequence = stopseq
            stoptime.shape_dist_traveled = odometer.dist_traveled(stoptime.stop,
                        stoptime.shape_dist_traveled if stoptime.shape_dist_traveled != -999999 else None)
            if stopseq == 0:
                # Force first arrival time to NULL
                stoptime.arrival_time = None
            if stopseq == n_stoptimes - 1:
                # Force last departure time to NULL
                stoptime.departure_time = None
            if stoptime.interpolated:
                to_interpolate.append(stoptime)
            else:
                if len(to_interpolate) > 0:
                    # Interpolate
                    if last_stoptime_with_time is None:
                        logger.error("Cannot interpolate missing time at trip start: %s" % trip)
                        for stti in to_interpolate:
                            # Use first defined time as fallback value.
                            stti.arrival_time = stoptime.arrival_time
                            stti.departure_time = stoptime.arrival_time
                    else:
                        tdist = stoptime.shape_dist_traveled - last_stoptime_with_time.shape_dist_traveled
                        ttime = stoptime.arrival_time - last_stoptime_with_time.departure_time
                        for stti in to_interpolate:
                            fdist = stti.shape_dist_traveled - last_stoptime_with_time.shape_dist_traveled
                            t = last_stoptime_with_time.departure_time + ttime * fdist // tdist
                            stti.arrival_time = t
                            stti.departure_time = t
                to_interpolate = []
                last_stoptime_with_time = stoptime
            stopseq += 1
        if len(to_interpolate) > 0:
            # Should not happen, but handle the case, we never know
            if last_stoptime_with_time is None:
                logger.error("Cannot interpolate missing time, no time at all: %s" % trip)
                # Keep times NULL (TODO: or remove the trip?)
            else:
                logger.error("Cannot interpolate missing time at trip end: %s" % trip)
                for stti in to_interpolate:
                    # Use last defined time as fallback value
                    stti.arrival_time = last_stoptime_with_time.departure_time
                    stti.departure_time = last_stoptime_with_time.departure_time

    if disable_normalization:
        logger.info("Skipping shapes and trips normalization")
    else:
        logger.info("Normalizing shapes and trips...")
        nshapes = 0
        ntrips = 0
        odometer = _Odometer()
        # Process shapes and associated trips
        for shape in dao.shapes(fltr=Shape.feed_id == feed_id, prefetch_points=True, batch_size=50):
            # Shape will be registered in the normalize
            odometer.normalize_and_register_shape(shape)
            for trip in dao.trips(fltr=(Trip.feed_id == feed_id) & (Trip.shape_id == shape.shape_id), prefetch_stop_times=True, prefetch_stops=True, batch_size=800):
                normalize_trip(trip, odometer)
                ntrips += 1
                if ntrips % 1000 == 0:
                    logger.info("%d trips, %d shapes" % (ntrips, nshapes))
                    dao.flush()
            nshapes += 1
            #odometer._debug_cache()
        # Process trips w/o shapes
        for trip in dao.trips(fltr=(Trip.feed_id == feed_id) & (Trip.shape_id == None), prefetch_stop_times=True, prefetch_stops=True, batch_size=800):
            odometer.register_noshape()
            normalize_trip(trip, odometer)
            ntrips += 1
            if ntrips % 1000 == 0:
                logger.info("%d trips" % ntrips)
                dao.flush()
        dao.flush()
        logger.info("Normalized %d trips and %d shapes" % (ntrips, nshapes))

    # Note: we expand frequencies *after* normalization
    # for performances purpose only: that minimize the
    # number of trips to normalize. We can do that since
    # the expansion is neutral trip-normalization-wise.
    logger.info("Expanding frequencies...")
    n_freq = 0
    n_exp_trips = 0
    trips_to_delete = []
    for frequency in gtfs.frequencies():
        trip_id = frequency.get('trip_id')
        if trip_id not in trip_ids:
            if lenient:
                logger.error("Trip ID '%s' in '%s' is invalid. Skipping frequency." % (trip_id, frequency))
                continue
            else:
                raise KeyError("Trip ID '%s' in '%s' is invalid." % (trip_id, frequency))
        trip = dao.trip(trip_id, feed_id=feed_id)
        start_time = _timetoint(frequency.get('start_time'))
        end_time = _timetoint(frequency.get('end_time'))
        headway_secs = _toint(frequency.get('headway_secs'))
        exact_times = _toint(frequency.get('exact_times'), Trip.TIME_APPROX)
        for trip_dep_time in range(start_time, end_time, headway_secs):
            # Here we assume departure time are all different.
            # That's a requirement in the GTFS specs, but this may break.
            # TODO Make the expanded trip ID generation parametrable.
            trip_id2 = trip.trip_id + "@" + fmttime(trip_dep_time)
            trip2 = Trip(feed_id, trip_id2, trip.route_id, trip.service_id,
                         wheelchair_accessible=trip.wheelchair_accessible,
                         bikes_allowed=trip.bikes_allowed,
                         exact_times=exact_times,
                         frequency_generated=True,
                         trip_headsign=trip.trip_headsign,
                         trip_short_name=trip.trip_short_name,
                         direction_id=trip.direction_id,
                         block_id=trip.block_id)
            trip2.stop_times = []
            base_time = trip.stop_times[0].departure_time
            for stoptime in trip.stop_times:
                arrtime = None if stoptime.arrival_time is None else stoptime.arrival_time - base_time + trip_dep_time
                deptime = None if stoptime.departure_time is None else stoptime.departure_time - base_time + trip_dep_time
                stoptime2 = StopTime(feed_id, trip_id2, stoptime.stop_id, stoptime.stop_sequence,
                            arrival_time=arrtime,
                            departure_time=deptime,
                            shape_dist_traveled=stoptime.shape_dist_traveled,
                            interpolated=stoptime.interpolated,
                            timepoint=stoptime.timepoint,
                            pickup_type=stoptime.pickup_type,
                            drop_off_type=stoptime.drop_off_type)
                trip2.stop_times.append(stoptime2)
            n_exp_trips += 1
            # This will add the associated stop times
            dao.add(trip2)
        # Do not delete trip now, as two frequency can refer to same trip
        trips_to_delete.append(trip)
        n_freq += 1
    for trip in trips_to_delete:
        # This also delete the associated stop times
        dao.delete(trip)
    dao.flush()
    dao.commit()
    logger.info("Expanded %d frequencies to %d trips." % (n_freq, n_exp_trips))

    logger.info("Feed '%s': import done." % feed_id)
