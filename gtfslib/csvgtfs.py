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
        self._header = six.next(rows)
        self._rows = rows
        self._factory = collections.namedtuple(objname, self._header)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self._header)

    def __iter__(self):
        return self

    def __next__(self):
        row = six.next(self._rows)
        dic = dict(zip(self._header, row))
        return self._factory(**dic)
        # return dic
    
    def next(self):
        return self.__next__()

class Python2or3Csv(object):
    
    def __init__(self, filesource, filename, encoding, dialect=csv.excel, **kwargs):
        if six.PY2:
            filedata = filesource.open(filename, 'rU')
        else:
            filedata = io.TextIOWrapper(filesource.open(filename, 'r'), encoding=encoding)
        self._csvreader = csv.reader(filedata, dialect=dialect, **kwargs)
        self._encoding = encoding
    
    def __iter__(self):
        return self
    
    def _convert(self, cell):
        cell = cell.strip()
        # Empty cell returns None
        if not cell:
            return None
        return cell
    
    def next(self):
        row = six.next(self._csvreader)
        return [ unicode(cell, self._encoding) for cell in row ]

    def __next__(self):
        row = six.next(self._csvreader)
        return [ cell for cell in row ]

def python2or3_csv(filesource, filename, encoding, dialect=csv.excel, **kwargs):
    if six.PY2:
        filedata = filesource.open(filename, 'rU')
    else:
        filedata = io.TextIOWrapper(filesource.open(filename, 'r'), encoding=encoding)
    csvreader = csv.reader(filedata, dialect=dialect, **kwargs)
    for row in csvreader:
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
            dict(obj='FeedInfo', getter='feedinfo', table='feed_info.txt'),
            dict(obj='Agency', getter='agencies', table='agency.txt'),
            dict(obj='Stop', getter='stops', table='stops.txt'),
            dict(obj='Route', getter='routes', table='routes.txt'),
            dict(obj='Trip', getter='trips', table='trips.txt'),
            dict(obj='StopTime', getter='stop_times', table='stop_times.txt'),
            dict(obj='Calendar', getter='calendars', table='calendar.txt'),
            dict(obj='CalendarDate', getter='calendar_dates', table='calendar_dates.txt'),
            dict(obj='Transfer', getter='transfers', table='transfers.txt')
    ]
    
    def __init__(self, filesource):
        self._filesource = filesource
        
    def load(self):
        for tbl in Gtfs.TABLES:
            setattr(Gtfs, tbl['getter'], self.make_getter(tbl['obj'], tbl['table']))
        return self

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self._filesource)

    def make_getter(self, name, filename):
        def getter(self):
            # myreader = Python2or3Csv(self._filesource, filename, 'utf-8')
            myreader = python2or3_csv(self._filesource, filename, 'utf-8')
            mytable = CsvTableFactory(name, myreader)
            return mytable
        return getter
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._filesource.close()
