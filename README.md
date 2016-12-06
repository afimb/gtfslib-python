# gtfslib-python
An open source library in python for reading GTFS files and computing various stats and indicators about Public Transport networks

[![Build Status](https://travis-ci.org/afimb/gtfslib-python.svg)](https://travis-ci.org/afimb/gtfslib-python)

This software is open source ([GPLv3](https://github.com/afimb/gtfslib-python/blob/master/LICENSE)); in particular, there is no warranty.

A more complete documentation can be found [in the wiki](https://github.com/afimb/gtfslib-python/wiki)

-> Pour des explications **en français**, voir [la page FR du wiki](https://github.com/afimb/gtfslib-python/wiki)

## Installation

(Optional) You may want to setup a virtual environment before:
(See https://virtualenv.readthedocs.org/ for more info.)

	$ virtualenv <ENV>
	$ . <ENV>/bin/activate

Download and install the lib:

	$ git clone git@github.com:afimb/gtfslib-python.git
	$ cd gtfslib-python
	$ pip install .
	$ gtfsdbloader --help

## Usage

### Command-line tool

	$ gtfsdbloader --help

### API tutorial

```python
from gtfslib.dao import Dao
dao = Dao("db.sqlite")
dao.load_gtfs("mygtfs.zip")
for stop in dao.stops():
	print(stop.stop_name)
for route in dao.routes(fltr=Route.route_type == Route.TYPE_BUS):
	print("%s: %d trips" % (route.route_long_name, len(route.trips)))
```

For more information [see here](https://github.com/afimb/gtfslib-python/wiki/API-usage-tutorial).

## Data model

The internal model used, GTFS', is close to GTFS but simplified / normalized / expanded for ease of use.

The main differences are:

* A calendar is a simple list of calendar dates (there is no date range, day of the week and positive/negative exceptions anymore).
* All optional fields with a default value are set (for example, pickup/dropoff types)
* Missing stop times are correctly interpolated, and marked with a flag.
* Shape distances are converted to meters and computed if missing.
* All frequencies are expanded to normal trips, and marked with a flag (TODO).
* ...

For the detail and more information [see here](https://github.com/afimb/gtfslib-python/wiki/Internal-model---GTFS').
