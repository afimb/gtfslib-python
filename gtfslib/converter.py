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
    Trip, StopTime, Transfer
from gtfslib.utils import timing, fmttime
from gtfslib.spatial import DistanceCache

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

@timing
def _convert_gtfs_model(feed_id, gtfs, dao, lenient=False):
    
    feedinfo2 = FeedInfo(feed_id)
    dao.add(feedinfo2)
    logger.info("Importing feed ID '%s'" % feed_id)

    logger.info("Importing agencies...")
    n_agencies = 0
    single_agency = None
    agency_ids = set()
    for agency in gtfs.agencies():
        aval = vars(agency)
        # agency_id is optional only if we have a single agency
        if n_agencies == 0 and aval.get('agency_id') is None:
            aval['agency_id'] = ''
        agency2 = Agency(feed_id, **aval)
        if n_agencies == 0:
            single_agency = agency2
        else:
            single_agency = None
        n_agencies += 1
        dao.add(agency2)
        agency_ids.add(agency2.agency_id)
    dao.flush()
    logger.info("Imported %d agencies" % n_agencies)

    def import_stop(stop, stoptype, item_ids, station_ids=None):
        sval = vars(stop)
        sval['location_type'] = _toint(sval.get('location_type'), Stop.TYPE_STOP)
        if sval['location_type'] != stoptype:
            return
        sval['wheelchair_boarding'] = _toint(sval.get('wheelchair_boarding'), Stop.WHEELCHAIR_UNKNOWN)
        lat = _tofloat(sval.get('stop_lat'), None)
        lon = _tofloat(sval.get('stop_lon'), None)
        if lat is None or lon is None:
            if lenient:
                logger.error("Missing lat/lon for '%s', set to default (0,0)" % (stop, ))
                if lat is None:
                    lat = 0
                if lon is None:
                    lon = 0
            else:
                raise ValueError("Missing mandatory lat/lon for '%s'." % (stop, ))
        sval['stop_lat'] = lat
        sval['stop_lon'] = lon
        # This field has been renamed for consistency
        parent_id = sval.get('parent_station')
        sval['parent_station_id'] = parent_id if parent_id else None
        if parent_id and station_ids and parent_id not in station_ids:
            if lenient:
                logger.error("Parent station ID '%s' in '%s' is invalid, resetting." % (parent_id, stop))
                sval['parent_station_id'] = None
            else:
                raise KeyError("Parent station ID '%s' in '%s' is invalid." % (parent_id, stop))
        sval.pop('parent_station', None)
        stop2 = Stop(feed_id, **sval)
        dao.add(stop2)
        item_ids.add(stop2.stop_id)

    stop_ids = set()
    station_ids = set()
    logger.info("Importing stations and stops...")
    n_stations = n_stops = 0
    for station in gtfs.stops():
        import_stop(station, Stop.TYPE_STATION, station_ids)
        n_stations += 1
    for stop in gtfs.stops():
        import_stop(stop, Stop.TYPE_STOP, stop_ids, station_ids)
        n_stops += 1
    dao.flush()
    logger.info("Imported %d stations and %d stops" % (n_stations, n_stops))

    logger.info("Importing transfers...")
    n_transfers = 0
    for transfer in gtfs.transfers():
        tval = vars(transfer)
        from_stop_id = tval.get('from_stop_id')
        to_stop_id = tval.get('to_stop_id')
        for stop_id in (from_stop_id, to_stop_id):
            if stop_id not in station_ids and stop_id not in stop_ids:
                if lenient:
                    logger.error("Stop ID '%s' in '%s' is invalid, skipping." % (stop_id, transfer))
                    continue
                else:
                    raise KeyError("Stop ID '%s' in '%s' is invalid." % (stop_id, transfer))
        transfer = Transfer(feed_id, **tval)
        dao.add(transfer)
    dao.flush()
    logger.info("Imported %d transfers" % (n_transfers))
    
    logger.info("Importing routes...")
    n_routes = 0
    route_ids = set()
    for route in gtfs.routes():
        rval = vars(route)
        rval['route_type'] = int(route.route_type)
        agency_id = rval.get('agency_id')
        if (agency_id is None or len(agency_id) == 0) and single_agency is not None:
            # Route.agency is optional if only a single agency exists.
            agency_id = rval['agency_id'] = single_agency.agency_id
        if agency_id not in agency_ids:
            if lenient:
                logger.error("Agency ID '%s' in '%s' is invalid, skipping route." % (agency_id, route))
                continue
            else:
                raise KeyError("agency ID '%s' in '%s' is invalid." % (agency_id, route))
        route2 = Route(feed_id, **rval)
        dao.add(route2)
        route_ids.add(route2.route_id)
        n_routes += 1
    dao.flush()
    logger.info("Imported %d routes" % n_routes)

    logger.info("Importing calendars...")
    calanddates2 = {}
    for calendar in gtfs.calendars():
        calid = calendar.service_id
        calendar2 = Calendar(feed_id, calid)
        dates2 = []
        start_date = CalendarDate.fromYYYYMMDD(calendar.start_date)
        end_date = CalendarDate.fromYYYYMMDD(calendar.end_date)
        for d in CalendarDate.range(start_date, end_date.next_day()):
            if int(getattr(calendar, DOW_NAMES[d.dow()])):
                dates2.append(d)
        calanddates2[calid] = (calendar2, set(dates2))

    logger.info("Normalizing calendar dates...")
    for caldate in gtfs.calendar_dates():
        calid = caldate.service_id
        date2 = CalendarDate.fromYYYYMMDD(caldate.date)
        addremove = int(caldate.exception_type)
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
    
    logger.info("Importing trips...")
    n_trips = 0
    trip_ids = set()
    for trip in gtfs.trips():
        tval = vars(trip)
        tval['wheelchair_accessible'] = _toint(tval.get('wheelchair_accessible'), Trip.WHEELCHAIR_UNKNOWN)
        tval['bikes_allowed'] = _toint(tval.get('bikes_allowed'), Trip.BIKES_UNKNOWN)
        cal_id = trip.service_id
        if cal_id not in calendar_ids:
            if lenient:
                logger.error("Calendar ID '%s' in '%s' is invalid. Skipping trip." % (cal_id, trip))
                continue
            else:
                raise KeyError("Calendar ID '%s' in '%s' is invalid." % (cal_id, trip))
        route_id = trip.route_id
        if route_id not in route_ids:
            if lenient:
                logger.error("Route ID '%s' in '%s' is invalid. Skipping trip." % (route_id, trip))
                continue
            else:
                raise KeyError("Route ID '%s' in trip '%s' is invalid." % (route_id, trip))
        trip2 = Trip(feed_id, frequency_generated=False, **tval)
        dao.add(trip2)
        trip_ids.add(trip.trip_id)
        n_trips += 1
    dao.flush()
    logger.info("Imported %d trips" % n_trips)

    logger.info("Importing stop times...")
    n_stoptimes = 0
    for stoptime in gtfs.stop_times():
        stval = vars(stoptime)
        stopseq = _toint(stval.get('stop_sequence'))
        # Mark times to interpolate later on 
        arrtime = _timetoint(stval.get('arrival_time'), -999999)
        deptime = _timetoint(stval.get('departure_time'), -999999)
        if arrtime == -999999:
            arrtime = deptime
        if deptime == -999999:
            deptime = arrtime
        interp = arrtime < 0 and deptime < 0
        shpdist = _tofloat(stval.get('shape_dist_traveled'), -999999)
        pkptype = _toint(stval.get('pickup_type'), StopTime.PICKUP_DROPOFF_REGULAR)
        drptype = _toint(stval.get('dropoff_type'), StopTime.PICKUP_DROPOFF_REGULAR)
        trip_id = stoptime.trip_id
        if trip_id not in trip_ids:
            if lenient:
                logger.error("Trip ID '%s' in '%s' is invalid. Skipping stop time." % (trip_id, stoptime))
                continue
            else:
                raise KeyError("Trip ID '%s' in '%s' is invalid." % (trip_id, stoptime))
        stop_id = stoptime.stop_id
        if stop_id not in stop_ids:
            if lenient:
                logger.error("Stop ID '%s' in '%s' is invalid. Skipping stop time." % (stop_id, stoptime))
                continue
            else:
                raise KeyError("Trip ID '%s' in stoptime '%s' is invalid." % (stop_id, stoptime))
        stoptime2 = StopTime(feed_id, stoptime.trip_id, stoptime.stop_id,
                stop_sequence=stopseq, arrival_time=arrtime, departure_time=deptime,
                shape_dist_traveled=shpdist, interpolated=interp,
                pickup_type=pkptype, dropoff_type=drptype,
                stop_headsign=stval.get('stop_headsign'))
        dao.add(stoptime2)
        n_stoptimes += 1
        # Commit every now and then
        if n_stoptimes % 10000 == 0:
            dao.flush()
            logger.info("%d stop times" % n_stoptimes)
    dao.flush()
    logger.info("Imported %d stop times" % n_stoptimes)

    logger.info("Normalizing trips...")
    ntrips = 0
    dcache = DistanceCache()
    # TODO Disabled batching for now, replace by batching in python using our list of trip IDs.
    for trip in dao.trips(fltr=Trip.feed_id == feed_id, prefetch_stop_times=True, prefetch_stops=True):
        stopseq = 0
        n_stoptimes = len(trip.stop_times)
        distance = 0
        last_stop = None
        last_stoptime_with_time = None
        to_interpolate = []
        for stoptime in trip.stop_times:
            # TODO Handle shapes if present
            # TODO Interpolate missing departure/arrival times
            if last_stop is not None:
                distance += dcache.orthodromic_distance(last_stop, stoptime.stop)
            last_stop = stoptime.stop
            stoptime.stop_sequence = stopseq
            stoptime.shape_dist_traveled = distance
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

        ntrips += 1
        if ntrips % 1000 == 0:
            logger.info("%d trips" % ntrips)
            dao.flush()
    dao.flush()
    logger.info("Normalized %d trips" % ntrips)

    # Note: we expand frequencies *after* normalization
    # for performances purpose only: that minimize the
    # number of trips to normalize. We can do that since
    # the expansion is neutral trip-normalization-wise.
    logger.info("Expanding frequencies...")
    n_freq = 0
    n_exp_trips = 0
    trips_to_delete = []
    for frequency in gtfs.frequencies():
        fval = vars(frequency)
        trip_id = frequency.trip_id
        if trip_id not in trip_ids:
            if lenient:
                logger.error("Trip ID '%s' in '%s' is invalid. Skipping frequency." % (trip_id, frequency))
                continue
            else:
                raise KeyError("Trip ID '%s' in '%s' is invalid." % (trip_id, frequency))
        trip = dao.trip(trip_id, feed_id=feed_id)
        start_time = _timetoint(fval.get('start_time'))
        end_time = _timetoint(fval.get('end_time'))
        headway_secs = _toint(fval.get('headway_secs'))
        exact_times = _toint(fval.get('exact_times'), Trip.TIME_APPROX)
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
                            dropoff_type=stoptime.dropoff_type)
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
    logger.info("Expanded %d frequencies to %d trips." % (n_freq, n_exp_trips))

    logger.info("Feed '%s': import done." % feed_id)
