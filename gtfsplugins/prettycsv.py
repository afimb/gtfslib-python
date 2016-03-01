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

    def __init__(self, outfile, fieldnames, maxwidth=120, **kwds):
        if outfile:
            self._rows = None
            if not outfile.endswith('.csv'):
                outfile += '.csv'
            if six.PY2:
                self._csvfile = open(outfile, 'w')
            else:
                self._csvfile = io.TextIOWrapper(open(outfile, 'wb'), encoding='utf-8')
            self._csv = csv.DictWriter(self._csvfile, fieldnames=fieldnames, **kwds)
            self._csv.writeheader()
        else:
            self._maxwidth = int(maxwidth)
            self._csv = None
            self._fieldnames = fieldnames
            self._rows = []

    def writerow(self, row):
        if self._csv:
            if six.PY2:
                # Python str vs unicode is brain-dead
                row = { k: v.encode(encoding='utf-8') if isinstance(v, unicode) else str(v) for k, v in row.items() }
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
            colwidths = [ min(self._maxwidth, len(f)) for f in self._fieldnames ]
            for row in self._rows:
                for i in range(0, len(self._fieldnames)):
                    fieldname = self._fieldnames[i]
                    cell = row.get(fieldname)
                    l = min(self._maxwidth, len(str(cell)))
                    if cell and l > colwidths[i]:
                        colwidths[i] = l
            self._prettysep(colwidths)
            self._prettyprint(colwidths, self._fieldnames)
            self._prettysep(colwidths)
            for row in self._rows:
                rowlist = [ row.get(field) for field in self._fieldnames ]
                self._prettyprint(colwidths, rowlist)
            self._prettysep(colwidths)

    def _prettyprint(self, widths, row=None):
        s = "| "
        for width, cell in zip(widths, row):
            scell = "" if cell is None else str(cell)
            diff = width - len(scell)
            s += ' ' + (' ' * diff) + scell[:width] + ' |'
        print(s)

    def _prettysep(self, widths):
        s = "+-"
        for width in widths:
            s += '-' * (width + 1) + '-+'
        print(s)
