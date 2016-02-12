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

from inspect import isclass

import sqlalchemy
from sqlalchemy.orm import subqueryload
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm.util import aliased
from sqlalchemy.exc import InvalidRequestError

from gtfslib.converter import _convert_gtfs_model
from gtfslib.csvgtfs import Gtfs, ZipFileSource
from gtfslib.model import FeedInfo, Agency, Route, Calendar, CalendarDate, Stop, \
    Trip, StopTime, Transfer, Shape, Zone, FareAttribute, FareRule
from gtfslib.orm import _Orm
from gtfslib.utils import group_pairs

class Dao(object):
    """
    Note to developer: Please do not use fancy magic, such as automatically generating methods,
    as this may break auto-complete and thus make the use of this class more difficult.
    """

    def __init__(self, db="", sql_logging=False):
        if db == "" or db is None:
            # In-memory SQLite
            connect_url = "sqlite:///"
        if "://" in db:
            # User has provided a full path
            connect_url = db
        else:
            # Assume a SQLite file
            connect_url = "sqlite:///%s" % db
        engine = sqlalchemy.create_engine(connect_url, echo=sql_logging)
        self._orm = _Orm(engine)
        Session = sessionmaker(bind=engine)
        self._session = Session()
        self._stoptime1 = aliased(StopTime, name="first_stop_time")
        self._stoptime2 = aliased(StopTime, name="second_stop_time")
        self._transfer_fromstop = aliased(Stop, name="from_stop")
        self._transfer_tostop = aliased(Stop, name="to_stop")

    def session(self):
        return self._session

    def add(self, obj):
        self._session.add(obj)
        
    def add_all(self, objs):
        self._session.add_all(objs)

    def delete(self, obj):
        self._session.delete(obj)
        
    def delete_feed(self, feed_id):
        self._session.query(StopTime).filter(StopTime.feed_id == feed_id).delete(synchronize_session=False)
        self._session.query(Trip).filter(Trip.feed_id == feed_id).delete(synchronize_session=False)
        self._session.query(CalendarDate).filter(CalendarDate.feed_id == feed_id).delete(synchronize_session=False)
        self._session.query(Calendar).filter(Calendar.feed_id == feed_id).delete(synchronize_session=False)
        self._session.query(Route).filter(Route.feed_id == feed_id).delete(synchronize_session=False)
        self._session.query(Stop).filter(Stop.feed_id == feed_id).delete(synchronize_session=False)
        self._session.query(Agency).filter(Agency.feed_id == feed_id).delete(synchronize_session=False)
        self._session.query(FeedInfo).filter(FeedInfo.feed_id == feed_id).delete()

    def commit(self):
        self._session.commit()
        
    def flush(self):
        self._session.flush()

    def feed(self, feed_id=""):
        return self._session.query(FeedInfo).get(feed_id)

    def feeds(self):
        return self._session.query(FeedInfo).all()

    def agency(self, agency_id, feed_id="", prefetch_routes=False):
        query = self._session.query(Agency)
        if prefetch_routes:
            query = query.options(subqueryload('routes'))
        return query.get((feed_id, agency_id))
        
    def agencies(self, fltr=None, prefetch_routes=False):
        query = self._session.query(Agency)
        if fltr is not None:
            query = _AutoJoiner(self._orm, query, fltr).autojoin()
            query = query.filter(fltr)
        if prefetch_routes:
            query = query.options(subqueryload('routes'))
        return query.all()

    def zone(self, zone_id, feed_id="", prefetch_stops=False):
        query = self._session.query(Zone)
        if prefetch_stops:
            query = query.options(subqueryload('stops'))
        return query.get((feed_id, zone_id))

    def zones(self, fltr=None, prefetch_stops=False):
        query = self._session.query(Zone)
        if fltr is not None:
            query = query.filter(fltr)
        if prefetch_stops:
            query = query.options(subqueryload('stops'))
        return query.all()

    def stop(self, stop_id, feed_id="", prefetch_parent=True, prefetch_substops=True):
        query = self._session.query(Stop)
        if prefetch_parent:
            query = query.options(subqueryload('parent_station'))
        if prefetch_substops:
            query = query.options(subqueryload('sub_stops'))
        return query.get((feed_id, stop_id))
    
    def stops(self, fltr=None, prefetch_parent=True, prefetch_substops=True, batch_size=2):
        idquery = self._session.query(Stop.feed_id, Stop.stop_id)
        if fltr is not None:
            idquery = _AutoJoiner(self._orm, idquery, fltr).autojoin()
            idquery = idquery.filter(fltr)
        # Only query IDs first
        stopids = idquery.all()
        def query_factory():
            query = self._session.query(Stop)
            if prefetch_parent:
                query = query.options(subqueryload('parent_station'))
                if prefetch_substops:
                    query = query.options(subqueryload('sub_stops'))
            return query
        return self._page_query(query_factory, Stop.feed_id, Stop.stop_id, stopids, batch_size)

    def in_area(self, area):
        return (Stop.stop_lat >= area.min_lat) & (Stop.stop_lat <= area.max_lat) & (Stop.stop_lon >= area.min_lon) & (Stop.stop_lon <= area.max_lon)

    def transfer(self, from_stop_id, to_stop_id, feed_id="", prefetch_stops=True):
        query = self._session.query(Transfer)
        if prefetch_stops:
            query = query.options(subqueryload('from_stop'), subqueryload('to_stop'))
        return query.get((feed_id, from_stop_id, to_stop_id))

    def transfer_from_stop(self):
        return self._transfer_fromstop
    
    def transfer_to_stop(self):
        return self._transfer_tostop

    def transfers(self, fltr=None, stop_fltr=None, prefetch_stops=True):
        query = self._session.query(Transfer)
        if fltr is not None:
            query = query.filter(fltr)
        if stop_fltr is not None:
            query = query.join(self._transfer_fromstop, 'from_stop')
            query = query.join(self._transfer_tostop, 'to_stop')
            query = query.filter(stop_fltr)
        if prefetch_stops:
            query = query.options(subqueryload('from_stop'), subqueryload('to_stop'))
        return query.all()

    def route(self, route_id, feed_id=""):
        return self._session.query(Route).get((feed_id, route_id))

    def routes(self, fltr=None, prefetch_trips=False):
        query = self._session.query(Route)
        if fltr is not None:
            query = _AutoJoiner(self._orm, query, fltr).autojoin()
            query = query.filter(fltr)
        if prefetch_trips:
            query = query.options(subqueryload('trips'))
        return query.all()
    
    def calendar(self, service_id, feed_id="", prefetch_dates=True, prefetch_trips=False, prefetch_stop_times=False):
        query = self._session.query(Calendar)
        if prefetch_stop_times:
            prefetch_trips = True
        if prefetch_trips:
            loadopt = subqueryload('trips')
            if prefetch_stop_times:
                loadopt = loadopt.subqueryload('stop_times')
            query = query.options(loadopt)
        if prefetch_dates:
            query = query.options(subqueryload('dates'))
        return query.get((feed_id, service_id))
    
    def calendars(self, fltr=None, prefetch_dates=True, prefetch_trips=False):
        query = self._session.query(Calendar)
        if fltr is not None:
            query = _AutoJoiner(self._orm, query, fltr).autojoin()
            query = query.filter(fltr)
        if prefetch_dates:
            query = query.options(subqueryload('dates'))
        if prefetch_trips:
            query = query.options(subqueryload('trips'))
        return query.all()
    
    def calendar_dates(self, fltr=None, prefetch_calendars=True, prefetch_trips=False):
        query = self._session.query(CalendarDate)
        if fltr is not None:
            query = _AutoJoiner(self._orm, query, fltr).autojoin()
            query = query.filter(fltr)
        if prefetch_calendars:
            query = query.options(subqueryload('calendar'))
        if prefetch_trips:
            query = query.options(subqueryload('calendar.trips'))
        return query.all()

    def trip(self, trip_id, feed_id="", prefetch_stop_times=True):
        query = self._session.query(Trip)
        if prefetch_stop_times:
            query = query.options(subqueryload('stop_times'))
        return query.get((feed_id, trip_id))
    
    def trips(self, fltr=None, prefetch_stop_times=True, prefetch_routes=False, prefetch_stops=False, prefetch_calendars=False, batch_size=1000):
        idquery = self._session.query(Trip.feed_id, Trip.trip_id)
        if fltr is not None:
            idquery = _AutoJoiner(self._orm, idquery, fltr).autojoin()
            idquery = idquery.filter(fltr)
        # Only query IDs first
        tripids = idquery.all()
        def query_factory():
            query = self._session.query(Trip)
            _prefetch_stop_times = prefetch_stop_times
            if prefetch_stops:
                _prefetch_stop_times = True
            if _prefetch_stop_times:
                loadopt = subqueryload('stop_times')
                if prefetch_stops:
                    loadopt = loadopt.subqueryload('stop')
                query = query.options(loadopt)
            if prefetch_routes:
                query = query.options(subqueryload('route'))
            if prefetch_calendars:
                query = query.options(subqueryload('calendar'))
            return query
        return self._page_query(query_factory, Trip.feed_id, Trip.trip_id, tripids, batch_size)

    def stoptimes(self, fltr=None, prefetch_trips=True, prefetch_stop_times=False):
        query = self._session.query(StopTime)
        if fltr is not None:
            query = _AutoJoiner(self._orm, query, fltr).autojoin()
            query = query.filter(fltr)
        if prefetch_stop_times:
            prefetch_trips = True
        if prefetch_trips:
            loadopt = subqueryload('trip')
            if prefetch_stop_times:
                loadopt = loadopt.subqueryload('stop_times')
            query = query.options(loadopt)
        # Note: ID batching would be difficult to implement for StopTime
        # as StopTime do have a composite-primary composed of 3 elements
        # and 2 of them (trip_id + stop_seq) can't be grouped easily.
        return query.all()

    def hop_first(self):
        return self._stoptime1

    def hop_second(self):
        return self._stoptime2

    def hops(self, delta=1, fltr=None, prefetch_trips=True, prefetch_stop_times=False):
        query = self._session.query(self._stoptime1, self._stoptime2).filter((self._stoptime1.trip_id == self._stoptime2.trip_id) & ((self._stoptime1.stop_sequence + delta) == self._stoptime2.stop_sequence))
        if fltr is not None:
            query = _AutoJoiner(self._orm, query, fltr).autojoin()
            query = query.filter(fltr)
        if prefetch_stop_times:
            prefetch_trips = True
        if prefetch_trips:
            loadopt = subqueryload('trip')
            if prefetch_stop_times:
                loadopt = loadopt.subqueryload('stop_times')
            query = query.options(loadopt)
        return query.all()

    def shape(self, shape_id, feed_id="", prefetch_shape_points=True):
        query = self._session.query(Shape)
        if prefetch_shape_points:
            query = query.options(subqueryload('points'))
        return query.get((feed_id, shape_id))

    def shapes(self, fltr=None, prefetch_points=True):
        query = self._session.query(Shape)
        if fltr is not None:
            query = _AutoJoiner(self._orm, query, fltr).autojoin()
            query = query.filter(fltr)
        if prefetch_points:
            query = query.options(subqueryload('points'))
        return query.all()

    def fare_attribute(self, fare_id, feed_id="", prefetch_fare_rules=True):
        query = self._session.query(FareAttribute)
        if prefetch_fare_rules:
            query = query.options(subqueryload('fare_rules'))
        return query.get((feed_id, fare_id))

    def fare_attributes(self, fltr=None, prefetch_fare_rules=True):
        query = self._session.query(FareAttribute)
        if fltr is not None:
            query = _AutoJoiner(self._orm, query, fltr).autojoin()
            query = query.filter(fltr)
        if prefetch_fare_rules:
            query = query.options(subqueryload('fare_rules'))
        return query.all()

    def fare_rules(self, fltr=None, prefetch_fare_attributes=True):
        query = self._session.query(FareRule)
        if fltr is not None:
            query = _AutoJoiner(self._orm, query, fltr).autojoin()
            query = query.filter(fltr)
        if prefetch_fare_attributes:
            query = query.options(subqueryload('fare_attribute'))
        return query.all()

    def _page_query(self, query_factory, item_feed_id_column, item_id_column, ids, batch_size):
        if batch_size <= 0:
            batch_size = 1000
        for feed_id, item_ids in group_pairs(ids, batch_size):
            query = query_factory()
            query = query.filter((item_feed_id_column == feed_id) & (item_id_column.in_(item_ids)))
            batch = query.all()
            for item in batch:
                yield item

    def load_gtfs(self, filename, feed_id="", lenient=False, **kwargs):
        @transactional(self.session())
        def _do_load_gtfs():
            with Gtfs(ZipFileSource(filename)).load() as gtfs:
                _convert_gtfs_model(feed_id, gtfs, self, lenient, **kwargs)
        _do_load_gtfs()

class _AutoJoiner(object):

    def __init__(self, orm, query, fltr):
        self._orm = orm
        self._query = query
        self._fltr = fltr

    def autojoin(self):
        # 1. Determine the set of classes used in the query
        #    Usually, only one.
        query_classes = set()
        for col_desc in self._query.column_descriptions:
            _type = col_desc.get('type')
            if isclass(_type):
                clazz = _type
            else:
                expr = col_desc.get('expr')
                if hasattr(expr, 'class_'):
                    clazz = expr.class_
                else:
                    print("*** TODO Unrecognized class for expression: %s" % col_desc)
                    clazz = None
            if clazz is not None:
                query_classes.add(clazz)
        # 2. Determine the set of classes used in the filter
        self._join_tables = set()
        self._recurse_inspect(self._fltr)
        join_classes = set()
        for tbl in self._join_tables:
            join_class = self._orm.class_for_table(tbl)
            if join_class is not None:
                join_classes.add(join_class)
            else:
                # TODO Should we handle this?
                # print("Unknown class for table %s" % tbl)
                pass
        for clazz in query_classes:
            if clazz in join_classes:
                join_classes.remove(clazz)
        # 3. Compute all classes (query and join)
        all_classes = set()
        all_classes |= query_classes
        all_classes |= join_classes

        # 4. Ensure the join are connected
        #    Here we use the fact that the relationship graph has only 4 branches:
        #    Branch 1 is agency-route-trip
        #    Branch 2 is dates-calendar-trip
        #    Branch 3 is stops-stoptimes-trip
        #    Branch 4 is shape-trip
        #    With all branches in a star-like configuration with trip in the middle.
        branch1 = Agency in all_classes or Route in all_classes
        branch2 = CalendarDate in all_classes or Calendar in all_classes
        branch3 = Stop in all_classes or StopTime in all_classes
        branch4 = Shape in all_classes
        n_branches = sum(branch for branch in (branch1, branch2, branch3, branch4))
        if Trip not in all_classes and n_branches > 1:
            join_classes.add(Trip)
            all_classes.add(Trip)
        if Trip in all_classes:
            # Connect branch leafs to trip eventually
            if Agency in all_classes and not Route in all_classes:
                join_classes.add(Route)
            if CalendarDate in all_classes and not Calendar in all_classes:
                join_classes.add(Calendar)
            if Stop in all_classes and not StopTime in all_classes:
                join_classes.add(StopTime)

        # The order of join is important. We could have devised
        # a more generic approach by computing the paths between
        # each join to the query class, but since the number of
        # classes to join is really small we use a brute-force
        # approach: try to join each class in turn and if that
        # fails, re-queue it at the end and try another one...
        # Sort the classes in any order for stability of return values
        classes_to_join = sorted([ clazz for clazz in join_classes ], key=lambda clazz: str(clazz))
        timeout = 0
        while classes_to_join:
            clazz = classes_to_join.pop(0)
            timeout += 1
            try:
                self._query = self._query.join(clazz)
            except InvalidRequestError:
                if timeout > 10:
                    raise
                # Try later on
                classes_to_join.append(clazz)

        return self._query

    def _recurse_inspect(self, fltr_node):
        if hasattr(fltr_node, "table"):
            self._join_tables.add(fltr_node.table.name)
        for child in fltr_node.get_children():
            self._recurse_inspect(child)

def transactional(session):
    def wrap(func):
        def wrapped_func(*args, **kwargs):
            # No need to open the transaction
            # as it is automatically opened in
            # non auto-commit mode.
            try:
                ret = func(*args, **kwargs)
                session.commit()
                return ret
            except:
                session.rollback()
                raise
        return wrapped_func
    return wrap
