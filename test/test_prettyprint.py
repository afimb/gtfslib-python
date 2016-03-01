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

import sys
import unittest
import six
from gtfsplugins.prettycsv import PrettyCsv

class TestPrettyPrinter(unittest.TestCase):

    def test_prettyprinter(self):
        # Capture standard output
        saved_stdout = sys.stdout
        try:
            out = six.StringIO()
            sys.stdout = out
            with PrettyCsv(None, fieldnames=[ 'col1', 'col2' ], maxwidth=5) as csv:
                csv.writerow({ 'col1': 1, 'col2': 2 })
                csv.writerow({ 'col1': 11, 'col2': 'foobarbaz' })
            output = out.getvalue().strip()
        finally:
            sys.stdout = saved_stdout
        self.assertEqual("+------+-------+\n"+
                         "| col1 |  col2 |\n"+
                         "+------+-------+\n"+
                         "|    1 |     2 |\n"+
                         "|   11 | fooba |\n"+
                         "+------+-------+", output)

if __name__ == '__main__':
    unittest.main()
