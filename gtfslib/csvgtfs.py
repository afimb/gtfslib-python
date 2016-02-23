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
import collections
import csv
import io
import six
import zipfile

class CsvTableFactory(object):

    def __init__(self, objname, rows):
        self._header = [ self._strip_and_nullify(item) for item in six.next(rows) ]
        if self._header[0].startswith(six.u('\ufeff')):
            self._header[0] = self._header[0][1:]
        self._rows = rows
        self._factory = collections.namedtuple(objname, self._header)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self._header)

    def __iter__(self):
        return self

    def _strip_and_nullify(self, item):
        ret = item.strip()
        if len(ret) == 0:
            return None
        return ret

    def __next__(self):
        row = [ self._strip_and_nullify(item) for item in six.next(self._rows) ]
        args = dict(six.moves.zip_longest(self._header, row, fillvalue=None))
        # return self._factory(**args)
        # Directly return the dictionary, do not bother with an object creation
        # (the first thing the client does is converting the object to a dict...)
        return args
    
    def next(self):
        return self.__next__()

def python2or3_csv(filesource, filename, encoding, dialect=csv.excel, **kwargs):
    if six.PY2:
        filedata = filesource.open(filename, 'rU')
    else:
        filedata = io.TextIOWrapper(filesource.open(filename, 'r'), encoding=encoding)
    csvreader = csv.reader(filedata, dialect=dialect, **kwargs)
    for row in csvreader:
        if len(row) == 0:
            continue
        if six.PY2:
            yield [ unicode(cell, encoding) for cell in row ]
        else:
            yield row

class ZipFileSource(object):
    
    def __init__(self, inputfile):
        self._zipfile = zipfile.ZipFile(inputfile)
    
    def open(self, filename, mode='rU'):
        return self._zipfile.open(filename, mode)
    
    def close(self):
        self._zipfile.close()

class Gtfs(object):
    TABLES = [
            dict(obj='GtfsFeedInfo', getter='feedinfo', table='feed_info.txt', optional=True),
            dict(obj='GtfsAgency', getter='agencies', table='agency.txt'),
            dict(obj='GtfsStop', getter='stops', table='stops.txt'),
            dict(obj='GtfsRoute', getter='routes', table='routes.txt'),
            dict(obj='GtfsTrip', getter='trips', table='trips.txt'),
            dict(obj='GtfsStopTime', getter='stop_times', table='stop_times.txt'),
            dict(obj='GtfsCalendar', getter='calendars', table='calendar.txt', optional=True),
            dict(obj='GtfsCalendarDate', getter='calendar_dates', table='calendar_dates.txt', optional=True),
            dict(obj='GtfsTransfer', getter='transfers', table='transfers.txt', optional=True),
            dict(obj='GtfsFrequency', getter='frequencies', table='frequencies.txt', optional=True),
            dict(obj='GtfsShape', getter='shapes', table='shapes.txt', optional=True),
            dict(obj='GtfsFareAttribute', getter='fare_attributes', table='fare_attributes.txt', optional=True),
            dict(obj='GtfsFareRule', getter='fare_rules', table='fare_rules.txt', optional=True)
    ]
    
    def __init__(self, filesource):
        self._filesource = filesource
        
    def load(self):
        for tbl in Gtfs.TABLES:
            setattr(Gtfs, tbl['getter'], self.make_getter(tbl['obj'], tbl['table'], optional=tbl.get('optional')))
        return self

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self._filesource)

    def make_getter(self, name, filename, optional=False):
        def getter(self):
            try:
                myreader = python2or3_csv(self._filesource, filename, 'utf-8')
                mytable = CsvTableFactory(name, myreader)
                return mytable
            except KeyError:
                # If table is optional, return empty iterator
                if optional:
                    return iter(())
                else:
                    raise KeyError("Required table '%s' not found in GTFS." % filename)
        return getter
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._filesource.close()
