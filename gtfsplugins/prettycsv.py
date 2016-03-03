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

import io
import six
import csv

class PrettyCsv(object):
    """Act as a csv DictWriter or console pretty-printer, according to whether outfile is set or not."""

    def __init__(self, outfile, fieldnames=None, maxwidth=120, **kwargs):
        self._fieldnames = fieldnames
        if outfile:
            self._rows = None
            if not outfile.endswith('.csv'):
                outfile += '.csv'
            if six.PY2:
                self._csvfile = open(outfile, 'w')
            else:
                self._csvfile = io.TextIOWrapper(open(outfile, 'wb'), encoding='utf-8')
            self._csv = csv.writer(self._csvfile, **kwargs)
            if self._fieldnames is not None:
                # Write header
                self._csv.writerow(fieldnames)
        else:
            self._maxwidth = int(maxwidth)
            self._csv = None
            self._rows = []

    def writerow(self, row):
        if isinstance(row, dict):
            if self._fieldnames is None:
                raise Exception("You can't add a row as dictionnary w/o specifying fieldnames!")
            row = [ row.get(fieldname, None) for fieldname in self._fieldnames ]
        if self._csv:
            if six.PY2:
                # Python str vs unicode is brain-dead
                row = [ v.encode(encoding='utf-8') if isinstance(v, unicode) else str(v) for v in row ]
            self._csv.writerow(row)
        if self._rows is not None:
            self._rows.append(row)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        if self._csv:
            self._csvfile.close()
        else:
            if self._fieldnames is not None:
                allrows = [ self._fieldnames ] + self._rows
            else:
                allrows = self._rows
            ncols = max(len(row) for row in allrows)
            colwidths = [ 0 for i in range(0, ncols) ]
            for row in allrows:
                for i in range(0, len(row)):
                    cell = row[i]
                    l = min(self._maxwidth, len(str(cell)))
                    if cell and l > colwidths[i]:
                        colwidths[i] = l
            if self._fieldnames is not None:
                self._prettysep(colwidths)
                self._prettyprint(colwidths, self._fieldnames)
            self._prettysep(colwidths)
            for row in self._rows:
                self._prettyprint(colwidths, row)
            self._prettysep(colwidths)

    def _prettyprint(self, widths, row=None):
        s = "|"
        for width, cell in six.moves.zip_longest(widths, row, fillvalue=None):
            scell = "" if cell is None else str(cell)
            diff = width - len(scell)
            s += ' ' + (' ' * diff) + scell[:width] + ' |'
        print(s)

    def _prettysep(self, widths):
        s = "+"
        for width in widths:
            s += '-' * (width + 1) + '-+'
        print(s)
