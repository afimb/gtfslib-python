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

class DemoPlugin(object):
    """
    Documentation for the demo plugin.
    This plugin is a demo to illustrate how to implement a plugin.

    Arguments:
      --printtrips Print all filtered trips.
    """

    def __init__(self):
        pass

    def run(self, context, printtrips=False, **kwargs):
        print("%s is running." % (self.__class__.__name__))
        print("Extra arguments: %s" % (kwargs))
        if printtrips:
            for trip in context.dao().trips(fltr=context.args.filter):
                print(trip)