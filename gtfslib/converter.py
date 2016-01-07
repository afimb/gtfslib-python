#!/usr/bin/python
# -*- coding: utf-8 -*-
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
    for agency in gtfs.agencies():
        agency2 = Agency(feed_id, **vars(agency))
        dao.add(agency2)
        n_agencies += 1
    dao.flush()
    logger.info("Imported %d agencies" % n_agencies)

    def import_stop(stop):
        sval = vars(stop)
        sval['wheelchair_boarding'] = _toint(sval.get('wheelchair_boarding'), Stop.WHEELCHAIR_UNKNOWN)
        # This field has been renamed for consistency
        parent_id = sval.get('parent_station')
        sval['parent_station_id'] = parent_id if parent_id else None
        del sval['parent_station']
        stop2 = Stop(feed_id, **sval)
        dao.add(stop2)
    
    logger.info("Importing stations and stops...")
    n_stations = n_stops = 0
    for station in gtfs.stops():
        if int(station.location_type) == Stop.TYPE_STATION:
            import_stop(station)
            n_stations += 1
    for stop in gtfs.stops():
        if int(stop.location_type) == Stop.TYPE_STOP:
            import_stop(stop)
            n_stops += 1
    dao.flush()
    logger.info("Imported %d stations and %d stops" % (n_stations, n_stops))
    
    logger.info("Importing routes...")
    n_routes = 0
    for route in gtfs.routes():
        rval = vars(route)
        rval['route_type'] = int(route.route_type)
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
        for stoptime in trip.stop_times:
            # TODO Handle shapes if present
            # TODO Interpolate missing departure/arrival times
            # TODO Set first arrival / last departure time to NULL
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
            stopseq += 1
        ntrips += 1
        if ntrips % 1000 == 0:
            logger.info("%d trips" % ntrips)
            dao.flush()
    logger.info("Normalized %d trips" % ntrips)
    dao.flush()
    
    dao.commit()
    logger.info("Feed '%s': import done." % feed_id)
