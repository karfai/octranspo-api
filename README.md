Summary
=======
This is a simple wrapper around the OCTranspo (public transit service in Ottawa, ON, Canada). It's based off of the publicly available GTFS (http://code.google.com/transit/spec/transit_feed_specification.html) data for the service (http://www.gtfs-data-exchange.com/agency/oc-transpo/, http://www.octranspo1.com/files/google_transit.zip).

A prototype instance has been deployed to heroku as http://octranspo-api.heroku.com/.

Source code
===========

The source is available from github (https://github.com/karfai/octranspo-api) licensed under the GPL (v3).

Authors
=======
Don Kelly <karfai@gmail.com>  
https://github.com/karfai/  
http://www.strangeware.ca/  

Outstanding issues
==================
Currently (20110820), the service time zone **is not** considered. This will be fixed **soon**.

API
===
The application provides JSON formatted data in response to a number HTTP requests:

Stop information
----------------
NOTE: These are informational queries to access stop information **regardless** of service period.

- /stops
  - Provides a list of all the stops in the database. Provides basic stop information (number, name, latitude and longitude). **Achtung**: This is an expensive query that will take many seconds to return.

- /stops/:number
  - Provides details about a single stop associated with the stop number that appears in the physical signage for the stop.

- /stops_by_name/:name
  - Provides a set of stop details where the string in the :name parameter appears in the stop description.

- /stops/:number/nearby[?within=:distance in meters]
  - Provides details about stops geographically near the stop specified by number. The optional "within" parameter can be used to change the distance tolerance (defaults to 400m).

- /stops_nearby/:lat/:lon[?within=:distance in meters]
  - Provides a set of stops geographically near the latitude and longitude specified in the request. The optional "within" parameter can be used to change the distance tolerance (defaults to 400m).

- /stops_nearby/:lat/:lon/closest
  - Provides the stop details for the stop closest to the provided coordinates.

Schedule information
--------------------
- /service_periods
  - Provides all of the different schedule sets for the current schedule. This covers issues like Saturday and Sunday service.

- /service_periods/:id
  - Provides details about a particular period, by id.

- /service_periods/current
  - Provides details about the active schedule (using the time of the server).

Travel
------
NOTE: These requests are run within the **current service period**.

- /arrivals/:stop_number[?minutes=:number]
  - Provides upcoming (static) arrivals to the stop specified by number. The results from this request encode a JOIN of several tables that should provide enough information to encode a "bus". The optional "number" parameter can be used to specific a future time window in minutes. This defaults to 15 minutes.

- /destinations/:trip_id/:sequence[?range=:number]
  - Provides details about the upcoming stops (static) on the route identified using "trip_id" and "sequence" information obtained via a request to "/arrivals" or a previous "/destinations" request. The results from this request are in the same format as the "/arrivals" request. The optional "range" parameter can be used to control the number of upcoming stops. The default value is 10.

**NOTE**: Since this data is mined from the static schedule and since the current position of a trip is **not available** as a live feed from the provider, it requires the use of :sequence to understand where the "bus" currently appears on the route trip. Calculating a :sequence correlated to the current position of the vehicle is left as an **exercise for the reader** (hint: /stops_nearby/.../closest OR a **functioning live feed**).

Examples
========
Request stops in the vicinity of Bell St N and the Queensway

    > curl "http://octranspo-api.heroku.com/stops_nearby/45.40412/-75.7405"
    [{"id":2586,"label":"NA430","number":8055,"name":"COLOMBINE / CHARDON","lat":45.4076,"lon":-75.73925},{"id":2588,"label":"NA440","number":8056,"name":"SIR FREDERICK BANTING / EGLANTINE","lat":45.40535,"lon":-75.741531},{"id":2603,"label":"NA910","number":3011,"name":"TUNNEY'S PASTURE 1B","lat":45.403652,"lon":-75.735596},{"id":2663,"label":"NC030","number":8058,"name":"SCOTT / SMIRLE","lat":45.402557,"lon":-75.737335}]

(output abbreviated)

Request arrivals at a stop from that set (3011 TUNNEY'S PASTURE 1B):

    > curl "http://octranspo-api.heroku.com/arrivals/3011"
    [{"stop":{"number":3011,"name":"TUNNEY'S PASTURE 1A"},"trip":{"id":12203,"route":"97","headsign":"Bayshore"},"arrival":66060,"departure":66060,"sequence":26},{"stop":{"number":3011,"name":"TUNNEY'S PASTURE 1A"},"trip":{"id":12109,"route":"96","headsign":"Terry Fox"},"arrival":66360,"departure":66360,"sequence":13},{"stop":{"number":3011,"name":"TUNNEY'S PASTURE 1A"},"trip":{"id":13263,"route":"98","headsign":"Tunney's Pasture"},"arrival":66540,"departure":66540,"sequence":52}]

Request upcoming stops for a bus we got on (97 Bayshore @ T+66060s) further along the route (to announce the next stops):

    > curl "http://octranspo-api.heroku.com/destinations/12203/26?range=2"
    [{"stop":{"number":3012,"name":"WESTBORO 1A"},"trip":{"id":12203,"route":"97","headsign":"Bayshore"},"arrival":66180,"departure":66180,"sequence":27},{"stop":{"number":3013,"name":"DOMINION 1A"},"trip":{"id":12203,"route":"97","headsign":"Bayshore"},"arrival":66240,"departure":66240,"sequence":28}]

Technical details
=================
This application is a RESTful data service providing JSON formatted results. It's implemented in Ruby using Sinatra as the web front and DataMapper as the ORM. Location computations are done with the geokit ruby gem (I reckon I've checked all the kool buzzwords). More enlightenment could be achieved by reading the code.

**Warning** to ruby purists: The database "compiler" is built in python. It was written in a different mood. I make no apologies.

Deployment
==========
Setup
-----
1. Get the code.

> git clone git@github.com:karfai/octranspo-api.git

2. Get a recent ZIP archive of the GTFS data. It should be available from the sources mentioned above.

3. "Compile" the sqlite3 database (about 15 minutes)

> python compile-database.py :sqlite_db_name :gtfs_zip_filename

Deploy a local testing instance
-------------------------------
1. Local testing instance

> DATABASE_URL=sqlite://:path_to_dbfile rackup -p :port_number config.ru

The local-up.sh script is my testing script that probably tells you something meaningless about how I lay out my project directories. You could modify this if you like.

OR Deploy to heroku
-------------------
1. **Once**: create a heroku application

> (visit heroku.com to learn how to do this incantation)

2. **When the db changes**: Push the db (about 25-30 minutes)

> heroku db:push sqlite://$PWD/:db_file_name

3. Deploy to heroku

> git push heroku master