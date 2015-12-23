# gtfslib-python
An open source library in python for reading GTFS files and computing various stats and indicators about Public Transport networks

## Installation

(Optional) You may want to setup a virtual environment before:
(See https://virtualenv.readthedocs.org/ for more info.)

	$ virtualenv <ENV>
	$ . <ENV>/bin/activate

Download and install the lib:

	$ git clone git@github.com:afimb/gtfslib-python.git
	$ cd gtfslib-python
	$ pip install
	$ gtfsdbloader --help

## Usage

### Command-line tool

	$ gtfsdbloader --help

### API tutorial

Import and create a DAO object, giving an optional database to operate on. If no database is provided, the data will be loaded to memory (so will not be saved to disk of course).

	from gtfslib.dao import Dao
	dao = Dao("db.sqlite")

If a simple filename is given, SQLite is assumed. In order to use other databases (PostgreSQL), use something like:

	dao = Dao("postgresql://gtfs@localhost/gtfs")

To load a GTFS into the database, normalizing it (conversion of calendars, trips, stop times, frequencies...):

	dao.load_gtfs("mygtfs.zip")

In order to load multiple GTFS at the same time, you need to provide a unique ID (here 'sncf'):

	dao.load_gtfs("sncf.gtfs.zip", feed_id="sncf")

To delete an entire feed and all attached objects (safe to use if the feed does not exists), or to reload again on top of previous data:

	dao.delete_feed("sncf")

You can now access objects to work on, for example a single object via it's ID (here route ID 'R1' from the default feed):

	route = dao.route('R1')
	print(route)

Or a list of all objects (here a list of all stops of all feeds):

	for stop in dao.stops():
		print(stop.stop_name)

Or a filter of all objects corresponding to some criteria, for example

	gares = dao.stops(fltr=Stop.stop_name.ilike("%gare%"))

Linked objects are "transparently" accessible via fields (for example: `route.trips`).
If they are not pre-loaded during the initial query, they will be lazily loaded at the time of first-access.

	for route in dao.routes(fltr=Route.route_type == Route.TYPE_BUS):
		# The following will issue a SELECT per route:
		print(len(route.trips))

You can say which data to pre-fetch. The same query, here pre-fetching route trips (a total of TWO selects only):

	for route in dao.routes(..., prefetch_trips=True):
		# Trips are pre-loaded
		print(len(route.trips))

For processing a large quantity of data, you can batch them (available only for stops, trips and stoptimes). The following will transparently issue a new SELECT every 1000 trips:

	for trip in dao.trips(batch_size=1000):
		... do something with trip ...

TODO: complex queries, SQL print
