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

from sqlalchemy.orm import mapper, relationship, backref, clear_mappers
from sqlalchemy.orm.relationships import foreign
from sqlalchemy.sql.schema import Column, MetaData, Table, ForeignKey, \
    ForeignKeyConstraint, Index
from sqlalchemy.sql.sqltypes import String, Integer, Float, Date, Boolean

from gtfslib.model import FeedInfo, Agency, Stop, Route, Calendar, CalendarDate, \
    Trip, StopTime, Transfer, Shape, ShapePoint, Zone, FareAttribute, FareRule


# ORM Mappings
class _Orm(object):

    def __init__(self, engine, schema=None):
        self._metadata = MetaData(schema=schema)
        self.mappers = []

        _feedinfo_id_column = Column('feed_id', String, primary_key=True)
        _agency_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True)
        _route_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True)
        _feedinfo_mapper = Table('feed_info', self._metadata,
                    _feedinfo_id_column,
                    Column('feed_publisher_name', String),
                    Column('feed_publisher_url', String),
                    Column('feed_contact_email', String), # Non-standard (yet) field
                    Column('feed_contact_url', String), # Non-standard (yet) field
                    Column('feed_lang', String),
                    Column('feed_start_date', Date),
                    Column('feed_end_date', Date),
                    Column('feed_version', String))
        self.mappers.append(mapper(FeedInfo, _feedinfo_mapper, properties={
        }))

        _agency_id_column = Column('agency_id', String, primary_key=True)
        _route_agency_id_column = Column('agency_id', String, nullable=False)
        _agency_mapper = Table('agency', self._metadata,
                    _agency_feed_id_column,
                    _agency_id_column,
                    Column('agency_name', String, nullable=False),
                    Column('agency_url', String, nullable=False),
                    Column('agency_timezone', String, nullable=False),
                    Column('agency_lang', String),
                    Column('agency_phone', String),
                    Column('agency_fare_url', String),
                    Column('agency_email', String))
        self.mappers.append(mapper(Agency, _agency_mapper, properties={
            'feed' : relationship(FeedInfo, backref=backref('agencies', cascade="all,delete-orphan"),
                                  primaryjoin=_feedinfo_id_column == foreign(_agency_feed_id_column))
        }))

        _zone_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True)
        _zone_id_column = Column('zone_id', String, primary_key=True)
        _zone_mapper = Table('zones', self._metadata,
                    _zone_feed_id_column,
                    _zone_id_column)
        self.mappers.append(mapper(Zone, _zone_mapper, properties={
            'feed' : relationship(FeedInfo, backref=backref('zones', cascade="all,delete-orphan"),
                                  primaryjoin=_feedinfo_id_column == foreign(_zone_feed_id_column))
        }))

        _stop_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True)
        _stop_id_column = Column('stop_id', String, primary_key=True)
        _stop_parent_id_column = Column('parent_station_id', String, nullable=True)
        _stop_zone_id_column = Column('zone_id', String, nullable=True)
        _stop_mapper = Table('stops', self._metadata,
                    _stop_feed_id_column,
                    _stop_id_column,
                    _stop_parent_id_column,
                    Column('location_type', Integer, nullable=False),
                    Column('stop_name', String, nullable=False),
                    Column('stop_lat', Float, nullable=False),
                    Column('stop_lon', Float, nullable=False),
                    Column('wheelchair_boarding', Integer, nullable=False),
                    Column('stop_code', String),
                    Column('stop_desc', String),
                    _stop_zone_id_column,
                    Column('stop_url', String),
                    Column('stop_timezone', String),
                    ForeignKeyConstraint(['feed_id', 'parent_station_id'], ['stops.feed_id', 'stops.stop_id']),
                    ForeignKeyConstraint(['feed_id', 'zone_id'], ['zones.feed_id', 'zones.zone_id']),
                    # TODO Make those index parametrable
                    Index('idx_stops_lat', 'stop_lat'),
                    Index('idx_stops_lon', 'stop_lon'),
                    Index('idx_stops_code', 'feed_id', 'stop_code'),
                    Index('idx_stops_zone', 'feed_id', 'zone_id'),
                    Index('idx_stops_parent', 'feed_id', 'parent_station_id'))
        self.mappers.append(mapper(Stop, _stop_mapper, properties={
            'feed' : relationship(FeedInfo, backref=backref('stops', cascade="all,delete-orphan"),
                                  primaryjoin=_feedinfo_id_column == foreign(_stop_feed_id_column)),
            'sub_stops' : relationship(Stop, remote_side=[_stop_feed_id_column, _stop_parent_id_column], uselist=True,
                                       primaryjoin=(_stop_parent_id_column == foreign(_stop_id_column)) & (_stop_feed_id_column == _stop_feed_id_column)),
            'parent_station' : relationship(Stop, remote_side=[_stop_feed_id_column, _stop_id_column],
                                       primaryjoin=(_stop_id_column == foreign(_stop_parent_id_column)) & (_stop_feed_id_column == _stop_feed_id_column)),
            'zone' : relationship(Zone, backref=backref('stops', cascade="all,delete-orphan"),
                                   primaryjoin=(_zone_id_column == foreign(_stop_zone_id_column)) & (_zone_feed_id_column == _stop_feed_id_column))
        }))

        _transfer_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True)
        _transfer_from_stop_id_column = Column('from_stop_id', String, primary_key=True)
        _transfer_to_stop_id_column = Column('to_stop_id', String, primary_key=True)
        _transfer_mapper = Table('transfers', self._metadata,
                    _transfer_feed_id_column,
                    _transfer_from_stop_id_column,
                    _transfer_to_stop_id_column,
                    Column('transfer_type', Integer, nullable=False),
                    Column('min_transfer_time', Integer),
                    ForeignKeyConstraint(['feed_id', 'from_stop_id'], ['stops.feed_id', 'stops.stop_id']),
                    ForeignKeyConstraint(['feed_id', 'to_stop_id'], ['stops.feed_id', 'stops.stop_id']),
                    Index('idx_transfer_from', 'feed_id', 'from_stop_id'),
                    Index('idx_transfer_to', 'feed_id', 'to_stop_id'))
        self.mappers.append(mapper(Transfer, _transfer_mapper, properties={
            'feed' : relationship(FeedInfo, backref=backref('transfers', cascade="all,delete-orphan"),
                                  primaryjoin=_feedinfo_id_column == foreign(_transfer_feed_id_column)),
            'from_stop' : relationship(Stop, backref=backref('from_transfers', cascade='all', uselist=True), uselist=False,
                                       primaryjoin=(_transfer_from_stop_id_column == foreign(_stop_id_column)) & (_transfer_feed_id_column == _stop_feed_id_column)),
            'to_stop' : relationship(Stop, backref=backref('to_transfers', cascade='all', uselist=True), uselist=False,
                                     primaryjoin=(_transfer_to_stop_id_column == foreign(_stop_id_column)) & (_transfer_feed_id_column == _stop_feed_id_column))
        }))

        _route_id_column = Column('route_id', String, primary_key=True)
        _route_mapper = Table('routes', self._metadata,
                    _route_feed_id_column,
                    _route_id_column,
                    _route_agency_id_column,
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
        self.mappers.append(mapper(Route, _route_mapper, properties={
            'feed' : relationship(FeedInfo, backref=backref('routes', cascade="all,delete-orphan"),
                                    primaryjoin=_feedinfo_id_column == foreign(_route_feed_id_column)),
            'agency' : relationship(Agency, backref=backref('routes', cascade="all,delete-orphan"),
                                    primaryjoin=(_agency_id_column == foreign(_route_agency_id_column)) & (_agency_feed_id_column == _route_feed_id_column))
        }))

        _calendar_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True)
        _calendar_id_column = Column('service_id', String, primary_key=True)
        _calendar_mapper = Table('calendar', self._metadata,
                    _calendar_feed_id_column,
                    _calendar_id_column
                    )
        self.mappers.append(mapper(Calendar, _calendar_mapper, properties={
            'feed' : relationship(FeedInfo, backref=backref('calendars', cascade="all,delete-orphan"),
                                  primaryjoin=_feedinfo_id_column == foreign(_calendar_feed_id_column))
        }))

        _calendar_date_mapper = Table('calendar_dates', self._metadata,
                    Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True),
                    Column('service_id', String, primary_key=True),
                    Column('date', Date, primary_key=True),
                    ForeignKeyConstraint(['feed_id', 'service_id'], ['calendar.feed_id', 'calendar.service_id']),
                    # TOCHECK It seems a composite primary key on (a,b,c) does not need indexing on left elements,
                    # such as (a) and (a,b); but need on (a,c) for example.
                    Index('idx_calendar_dates_date', 'feed_id', 'date'))
        self.mappers.append(mapper(CalendarDate, _calendar_date_mapper, properties={
            'calendar' : relationship(Calendar, backref=backref('dates', cascade="all,delete-orphan"))
        }))

        _shape_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True)
        _shape_id_column = Column('shape_id', String, primary_key=True)
        _shape_mapper = Table('shapes', self._metadata,
                    _shape_feed_id_column,
                    _shape_id_column
                    )
        self.mappers.append(mapper(Shape, _shape_mapper, properties={
            'feed' : relationship(FeedInfo, backref=backref('shapes', cascade="all,delete-orphan"),
                                  primaryjoin=_feedinfo_id_column == foreign(_shape_feed_id_column))
        }))

        _shape_pt_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True)
        _shape_pt_shape_id_column = Column('shape_id', String, primary_key=True)
        _shape_pt_seq_column = Column('shape_pt_sequence', Integer, primary_key=True)
        _shape_pt_mapper = Table('shape_pts', self._metadata,
                    _shape_pt_feed_id_column,
                    _shape_pt_shape_id_column,
                    _shape_pt_seq_column,
                    Column('shape_dist_traveled', Float, nullable=False),
                    Column('shape_pt_lat', Float, nullable=False),
                    Column('shape_pt_lon', Float, nullable=False),
                    ForeignKeyConstraint(['feed_id', 'shape_id'], ['shapes.feed_id', 'shapes.shape_id']),
                    Index('idx_shape_pt_shape', 'feed_id', 'shape_id'))
        self.mappers.append(mapper(ShapePoint, _shape_pt_mapper, properties={
            # Note: here we specify foreign() on shape_pt feed_id column as there is no ownership relation of feed to shape_pts
            'shape' : relationship(Shape, backref=backref('points', order_by=_shape_pt_seq_column, cascade="all,delete-orphan"),
                                  primaryjoin=(_shape_id_column == foreign(_shape_pt_shape_id_column)) & (_shape_feed_id_column == foreign(_shape_pt_feed_id_column)))
        }))

        _trip_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True)
        _trip_id_column = Column('trip_id', String, primary_key=True)
        _trip_route_id_column = Column('route_id', String, nullable=False)
        _trip_calendar_id_column = Column('service_id', String, nullable=False)
        _trip_shape_id_column = Column('shape_id', String, nullable=True)
        _trip_mapper = Table('trips', self._metadata,
                    _trip_feed_id_column,
                    _trip_id_column,
                    _trip_route_id_column,
                    _trip_calendar_id_column,
                    _trip_shape_id_column,
                    Column('wheelchair_accessible', Integer, nullable=False),
                    Column('bikes_allowed', Integer, nullable=False),
                    Column('exact_times', Integer, nullable=False),
                    Column('frequency_generated', Boolean, nullable=False),
                    Column('trip_headsign', String),
                    Column('trip_short_name', String),
                    Column('direction_id', Integer),
                    Column('block_id', String),
                    ForeignKeyConstraint(['feed_id', 'route_id'], ['routes.feed_id', 'routes.route_id']),
                    ForeignKeyConstraint(['feed_id', 'service_id'], ['calendar.feed_id', 'calendar.service_id']),
                    ForeignKeyConstraint(['feed_id', 'shape_id'], ['shapes.feed_id', 'shapes.shape_id']),
                    Index('idx_trips_route', 'feed_id', 'route_id'),
                    Index('idx_trips_service', 'feed_id', 'service_id'))
        self.mappers.append(mapper(Trip, _trip_mapper, properties={
            'feed' : relationship(FeedInfo, backref=backref('trips', cascade="all,delete-orphan"),
                                  primaryjoin=_feedinfo_id_column == foreign(_trip_feed_id_column)),
            'route' : relationship(Route, backref=backref('trips', cascade="all,delete-orphan"),
                                   primaryjoin=(_route_id_column == foreign(_trip_route_id_column)) & (_route_feed_id_column == _trip_feed_id_column)),
            'calendar' : relationship(Calendar, backref=backref('trips', cascade="all,delete-orphan"),
                                      primaryjoin=(_calendar_id_column == foreign(_trip_calendar_id_column)) & (_calendar_feed_id_column == _trip_feed_id_column)),
            'shape' : relationship(Shape, backref=backref('trips', cascade="all,delete-orphan"),
                                      primaryjoin=(_shape_id_column == foreign(_trip_shape_id_column)) & (_shape_feed_id_column == _trip_feed_id_column))
        }))

        _stop_times_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True)
        _stop_times_trip_id_column = Column('trip_id', String, primary_key=True)
        _stop_seq_column = Column('stop_sequence', Integer, primary_key=True)
        _stop_times_stop_id_column = Column('stop_id', String, nullable=False)
        _stop_times_mapper = Table('stop_times', self._metadata,
                    _stop_times_feed_id_column,
                    _stop_times_trip_id_column,
                    _stop_seq_column,
                    _stop_times_stop_id_column,
                    Column('arrival_time', Integer, nullable=True),
                    Column('departure_time', Integer, nullable=True),
                    Column('interpolated', Boolean, nullable=False),
                    Column('shape_dist_traveled', Float, nullable=False),
                    Column('timepoint', Integer, nullable=False),
                    Column('pickup_type', Integer, nullable=False),
                    Column('drop_off_type', Integer, nullable=False),
                    Column('stop_headsign', String),
                    ForeignKeyConstraint(['feed_id', 'trip_id'], ['trips.feed_id', 'trips.trip_id']),
                    ForeignKeyConstraint(['feed_id', 'stop_id'], ['stops.feed_id', 'stops.stop_id']),
                    Index('idx_stop_times_stop', 'feed_id', 'stop_id'),
                    Index('idx_stop_times_sequence', 'feed_id', 'stop_sequence'))
        self.mappers.append(mapper(StopTime, _stop_times_mapper, properties={
            # Note: here we specify foreign() on stop_times feed_id column as there is no ownership relation of feed to stop_times
            'trip' : relationship(Trip, backref=backref('stop_times', order_by=_stop_seq_column, cascade="all,delete-orphan"),
                                  primaryjoin=(_trip_id_column == foreign(_stop_times_trip_id_column)) & (_trip_feed_id_column == foreign(_stop_times_feed_id_column))),
            'stop' : relationship(Stop, backref=backref('stop_times', cascade="all,delete-orphan"),
                                  primaryjoin=(_stop_id_column == foreign(_stop_times_stop_id_column)) & (_stop_feed_id_column == _stop_times_feed_id_column)),
        }))

        _fareattr_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'), primary_key=True)
        _fareattr_id_column = Column('fare_id', String, primary_key=True)
        _fareattr_mapper = Table('fare_attributes', self._metadata,
                    _fareattr_feed_id_column,
                    _fareattr_id_column,
                    Column('price', Float, nullable=False),
                    Column('currency_type', String, nullable=False),
                    Column('payment_method', Integer, nullable=False),
                    Column('transfers', Integer),
                    Column('transfer_duration', Integer))
        self.mappers.append(mapper(FareAttribute, _fareattr_mapper, properties={
            'feed' : relationship(FeedInfo, backref=backref('fare_attributes', cascade="all,delete-orphan"),
                                  primaryjoin=_feedinfo_id_column == foreign(_fareattr_feed_id_column))
        }))

        _farerule_feed_id_column = Column('feed_id', String, ForeignKey('feed_info.feed_id'))
        _farerule_id_column = Column('fare_id', String)
        # Use a dummy autoincrement numerical field for primary key,
        # as a primary key is mandatory, and the natural primary key
        # for the model (feed_id, fare_id, route+zones ids) do have
        # some fields that can be null.
        _farerule_rule_id_column = Column('fare_rule_id', Integer, primary_key=True, autoincrement=True)
        _farerule_route_id_column = Column('route_id', String, nullable=True)
        _farerule_origin_id_column = Column('origin_id', String, nullable=True)
        _farerule_destination_id_column = Column('destination_id', String, nullable=True)
        _farerule_contains_id_column = Column('contains_id', String, nullable=True)
        _farerule_mapper = Table('fare_rules', self._metadata,
                    _farerule_feed_id_column,
                    _farerule_id_column,
                    _farerule_rule_id_column,
                    _farerule_route_id_column,
                    _farerule_origin_id_column,
                    _farerule_destination_id_column,
                    _farerule_contains_id_column,
                    ForeignKeyConstraint(['feed_id', 'fare_id'], ['fare_attributes.feed_id', 'fare_attributes.fare_id']))
        self.mappers.append(mapper(FareRule, _farerule_mapper, properties={
            'fare_attribute' : relationship(FareAttribute, backref=backref('fare_rules', cascade="all,delete-orphan")),
            'route' : relationship(Route, backref=backref('fare_rules', cascade="all,delete-orphan"),
                            primaryjoin=(_route_id_column == foreign(_farerule_route_id_column)) & (_route_feed_id_column == _farerule_feed_id_column)),
            'origin' : relationship(Zone, backref=backref('origin_fare_rules', cascade="all,delete-orphan"),
                            primaryjoin=(_zone_id_column == foreign(_farerule_origin_id_column)) & (_zone_feed_id_column == _farerule_feed_id_column)),
            'destination' : relationship(Zone, backref=backref('destination_fare_rules', cascade="all,delete-orphan"),
                            primaryjoin=(_zone_id_column == foreign(_farerule_destination_id_column)) & (_zone_feed_id_column == _farerule_feed_id_column)),
            'contains' : relationship(Zone, backref=backref('contains_fare_rules', cascade="all,delete-orphan"),
                            primaryjoin=(_zone_id_column == foreign(_farerule_contains_id_column)) & (_zone_feed_id_column == _farerule_feed_id_column))
        }))

        self._metadata.create_all(engine)
        self._class_for_table = {}
        self._table_for_class = {}
        for _mapper in self.mappers:
            self._class_for_table[_mapper.mapped_table.name] = _mapper.class_
            self._table_for_class[_mapper.class_] = _mapper.mapped_table.name

    def class_for_table(self, tablename):
        """Return the class associated to a given table name.
           We implement ourselves this method as there does not seem a reliable way
           of getting this information from SqlAlchemy itself w/o some brittle hacking."""
        return self._class_for_table.get(tablename)

    def table_for_class(self, clazz):
        """Return the table name associated to a give entity class."""
        return self._table_for_class.get(clazz)
