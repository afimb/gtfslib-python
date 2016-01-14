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
    Trip, StopTime
from gtfslib.utils import timing
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
        if default_value is None:
            raise ValueError()
        return default_value
    return float(s)

@timing
def _convert_gtfs_model(feed_id, gtfs, dao):
    
    feedinfo2 = FeedInfo(feed_id)
    dao.add(feedinfo2)
    logger.info("Importing feed ID '%s'" % feed_id)

    logger.info("Importing agencies...")
    n_agencies = 0
    single_agency = None
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
    dao.flush()
    logger.info("Imported %d agencies" % n_agencies)

    def import_stop(stop, stoptype):
        sval = vars(stop)
        sval['location_type'] = _toint(sval.get('location_type'), Stop.TYPE_STOP)
        if sval['location_type'] != stoptype:
            return
        sval['wheelchair_boarding'] = _toint(sval.get('wheelchair_boarding'), Stop.WHEELCHAIR_UNKNOWN)
        # Replace None by some default value to allow missing lat/lon
        sval['stop_lat'] = _tofloat(sval.get('stop_lat'), None)
        sval['stop_lon'] = _tofloat(sval.get('stop_lon'), None)
        # This field has been renamed for consistency
        parent_id = sval.get('parent_station')
        sval['parent_station_id'] = parent_id if parent_id else None
        sval.pop('parent_station', None)
        stop2 = Stop(feed_id, **sval)
        dao.add(stop2)
    
    logger.info("Importing stations and stops...")
    n_stations = n_stops = 0
    for station in gtfs.stops():
        import_stop(station, Stop.TYPE_STATION)
        n_stations += 1
    for stop in gtfs.stops():
        import_stop(stop, Stop.TYPE_STOP)
        n_stops += 1
    dao.flush()
    logger.info("Imported %d stations and %d stops" % (n_stations, n_stops))
    
    logger.info("Importing routes...")
    n_routes = 0
    for route in gtfs.routes():
        rval = vars(route)
        rval['route_type'] = int(route.route_type)
        agency_id = rval.get('agency_id')
        if (agency_id is None or len(agency_id) == 0) and single_agency is not None:
            # Route.agency is optional if only a single agency exists.
            rval['agency_id'] = single_agency.agency_id
        route2 = Route(feed_id, **rval)
        dao.add(route2)
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
    for (calendar2, dates2) in calanddates2.values():
        calendar2.dates = [ d for d in dates2 ]
        dao.add(calendar2)
        n_calendars += 1
        n_caldates += len(calendar2.dates)
    dao.flush()
    logger.info("Imported %d calendars and %d dates" % (n_calendars, n_caldates))
    
    logger.info("Importing trips...")
    n_trips = 0
    for trip in gtfs.trips():
        tval = vars(trip)
        tval['wheelchair_accessible'] = _toint(tval.get('wheelchair_accessible'), Trip.WHEELCHAIR_UNKNOWN)
        tval['bikes_allowed'] = _toint(tval.get('bikes_allowed'), Trip.BIKES_UNKNOWN)
        trip2 = Trip(feed_id, **tval)
        dao.add(trip2)
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
    for trip in dao.trips(fltr=Trip.feed_id == feed_id, prefetch_stop_times=True, prefetch_stops=True, batch_size=10000):
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
    logger.info("Normalized %d trips" % ntrips)
    dao.flush()
    
    dao.commit()
    logger.info("Feed '%s': import done." % feed_id)
