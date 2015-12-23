# -*- coding: utf-8 -*-
"""
@author: Laurent GRÉGOIRE <laurent.gregoire@mecatran.com>
"""

from sqlalchemy.orm import mapper, relationship, backref
from sqlalchemy.sql.schema import Column, MetaData, Table, ForeignKey, \
    ForeignKeyConstraint, Index
from sqlalchemy.sql.sqltypes import String, Integer, Float, Date, Boolean

from gtfslib.model import FeedInfo, Agency, Stop, Route, Calendar, CalendarDate, \
    Trip, StopTime


# ORM Mappings
class _Orm(object):

    _metadata = MetaData()
    
    _feedinfo_mapper = Table('feed_info', _metadata,
                Column('feed_id', String, primary_key=True))
    mapper(FeedInfo, _feedinfo_mapper, properties={
    })
    
    _agency_mapper = Table('agency', _metadata,
                Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True),
                Column('agency_id', String, primary_key=True),
                Column('agency_name', String, nullable=False),
                Column('agency_url', String, nullable=False),
                Column('agency_timezone', String, nullable=False),
                Column('agency_lang', String),
                Column('agency_phone', String),
                Column('agency_fare_url', String))
    mapper(Agency, _agency_mapper, properties={
        'feed' : relationship(FeedInfo, backref=backref('agencies', cascade="all,delete-orphan"))
    })

    _stop_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True) 
    _stop_id_column = Column('stop_id', String, primary_key=True)
    _stop_mapper = Table('stops', _metadata,
                _stop_feed_id_column,
                _stop_id_column,
                Column('parent_station_id', String, nullable=True),
                Column('location_type', Integer, nullable=False),
                Column('stop_name', String, nullable=False),
                Column('stop_lat', Float, nullable=False),
                Column('stop_lon', Float, nullable=False),
                Column('wheelchair_boarding', Integer, nullable=False),
                Column('stop_code', String),
                Column('stop_desc', String),
                Column('zone_id', String),
                Column('stop_url', String),
                Column('stop_timezone', String),
                ForeignKeyConstraint(['feed_id', 'parent_station_id'], ['stops.feed_id', 'stops.stop_id']),
                # TODO Make those index parametrable
                Index('idx_stops_lat', 'stop_lat'),
                Index('idx_stops_lon', 'stop_lon'),
                Index('idx_stops_code', 'feed_id', 'stop_code'),
                Index('idx_stops_zone', 'feed_id', 'zone_id'),
                Index('idx_stops_parent', 'feed_id', 'parent_station_id'))
    mapper(Stop, _stop_mapper, properties={
        'feed' : relationship(FeedInfo, backref=backref('stops', cascade="all,delete-orphan")),
        'sub_stops' : relationship(Stop, backref=backref('parent_station', remote_side=[_stop_feed_id_column, _stop_id_column]))
    })
    
    _route_mapper = Table('routes', _metadata,
                Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True),
                Column('route_id', String, primary_key=True),
                Column('agency_id', String, nullable=False),
                Column('route_short_name', String),
                Column('route_long_name', String),
                Column('route_desc', String),
                Column('route_type', Integer, nullable=False),
                Column('route_url', String),
                Column('route_color', String),
                Column('route_text_color', String),
                ForeignKeyConstraint(['feed_id', 'agency_id'], ['agency.feed_id', 'agency.agency_id']),
                Index('idx_routes_agency', 'feed_id', 'agency_id'),
                Index('idx_routes_short_name', 'feed_id', 'route_short_name'),
                Index('idx_routes_type', 'feed_id', 'route_type'))
    mapper(Route, _route_mapper, properties={
        'feed' : relationship(FeedInfo, backref=backref('routes', cascade="all,delete-orphan")),
        'agency' : relationship(Agency, backref=backref('routes', cascade="all,delete-orphan"))
    })
    
    _calendar_mapper = Table('calendar', _metadata,
                Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True),
                Column('service_id', String, primary_key=True))
    mapper(Calendar, _calendar_mapper, properties={
        'feed' : relationship(FeedInfo, backref=backref('calendars', cascade="all,delete-orphan")),
    })
    
    _calendar_date_mapper = Table('calendar_dates', _metadata,
                Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True),
                Column('service_id', String, primary_key=True),
                Column('date', Date, primary_key=True),
                ForeignKeyConstraint(['feed_id', 'service_id'], ['calendar.feed_id', 'calendar.service_id']),
                # TOCHECK It seems a composite primary key on (a,b,c) does not need indexing on left elements,
                # such as (a) and (a,b); but need on (a,c) for example.
                Index('idx_calendar_dates_date', 'feed_id', 'date'))
    mapper(CalendarDate, _calendar_date_mapper, properties={
        'calendar' : relationship(Calendar, backref=backref('dates', cascade="all,delete-orphan"))
    })

    _trip_mapper = Table('trips', _metadata,
                Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True),
                Column('trip_id', String, primary_key=True),
                Column('route_id', String, nullable=False),
                Column('service_id', String, nullable=False),
                Column('wheelchair_accessible', Integer, nullable=False),
                Column('bikes_allowed', Integer, nullable=False),
                Column('exact_times', Integer, nullable=False),
                Column('trip_headsign', String),
                Column('trip_short_name', String),
                Column('direction_id', Integer),
                Column('block_id', String),
                ForeignKeyConstraint(['feed_id', 'route_id'], ['routes.feed_id', 'routes.route_id']),
                ForeignKeyConstraint(['feed_id', 'service_id'], ['calendar.feed_id', 'calendar.service_id']),
                Index('idx_trips_route', 'feed_id', 'route_id'),
                Index('idx_trips_service', 'feed_id', 'service_id'))
    mapper(Trip, _trip_mapper, properties={
        'feed' : relationship(FeedInfo, backref=backref('trips', cascade="all,delete-orphan")),
        'route' : relationship(Route, backref=backref('trips', cascade="all,delete-orphan")),
        'calendar' : relationship(Calendar, backref=backref('trips', cascade="all,delete-orphan"))
    })

    _stop_seq_column = Column('stop_sequence', Integer, primary_key=True)
    _stop_times_mapper = Table('stop_times', _metadata,
                Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True),
                Column('trip_id', String, primary_key=True),
                _stop_seq_column,
                Column('stop_id', String, nullable=False),
                Column('arrival_time', Integer, nullable=True),
                Column('departure_time', Integer, nullable=True),
                Column('interpolated', Boolean, nullable=False),
                Column('shape_dist_traveled', Float, nullable=False),
                Column('timepoint', Integer, nullable=False),
                Column('pickup_type', Integer, nullable=False),
                Column('dropoff_type', Integer, nullable=False),
                Column('stop_headsign', String),
                ForeignKeyConstraint(['feed_id', 'trip_id'], ['trips.feed_id', 'trips.trip_id']),
                ForeignKeyConstraint(['feed_id', 'stop_id'], ['stops.feed_id', 'stops.stop_id']),
                Index('idx_stop_times_stop', 'feed_id', 'stop_id'),
                Index('idx_stop_times_sequence', 'feed_id', 'stop_sequence'))
    mapper(StopTime, _stop_times_mapper, properties={
        'trip' : relationship(Trip, backref=backref('stop_times', order_by=_stop_seq_column, cascade="all,delete-orphan")),
        'stop' : relationship(Stop, backref=backref('stop_times', cascade="all,delete-orphan"))
    })

    def __init__(self, engine):
        self._metadata.create_all(engine)

