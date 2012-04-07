Summary
=======
This is a simple wrapper around the OCTranspo (public transit service in Ottawa, ON, Canada). It's based off of the publicly available GTFS (http://code.google.com/transit/spec/transit_feed_specification.html) data for the service (http://www.gtfs-data-exchange.com/agency/oc-transpo/, http://www.octranspo1.com/files/google_transit.zip).

A prototype instance has been deployed to heroku as http://octranspo-api.heroku.com/.

The sqlite3 database provided by the compiler tool is also suitable for using on a mobile device. With indexes, the typical size is typically less then 100MB.

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

- arrivals after 23:59 on a current day are stored in elapsed seconds from midnight of the previous day. A reasonable *start of service* time needs to be derived
- the time zone for the *schedule* needs to stored and delivered via /version
- the database might store the famous OCTranspo time skew

API
===
The application provides JSON formatted data in response to a number HTTP requests:

General
-------

- /version
  - list current versions of the feed and the api as well as global information about the schedule.

Stop information
----------------
NOTE: These are informational queries to access stop information **regardless** of service period.

- /stops
  - Provides a list of all the stops in the database. Provides basic stop information (number, name, latitude and longitude). **Achtung**: This is an expensive query that will take many seconds to return.

- /stops/:number
  - Provides details about a single stop associated with the stop number that appears in the physical signage for the stop.

- /stops/:number/nearby[?within=:distance in meters]
  - Provides details about stops near the specified stop. The optional "within" parameter can be used to change the distance tolerance (defaults to 400m).

- /stops/:number/nearby/closest
  - Provides details about the next closest stop.

- /stops/:number/routes
  - Provides a summary of routes which service the specified stop. Listed with the routes are the arrival times throughout the day and which days of the week the route is in service. This request could be used to populate a page that shows the printed schedules seen on physical signage.

- /stops/:number/routes/in_service
  - Provides a restricted set of route information limited to the current service period.

- /stops_by_name/:name
  - Provides a set of stop details where the string in the :name parameter appears in the stop description.

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

- /arrivals/:stop_number[?minutes=:number][&app_id=:id&api_key=:key]
  - Provides upcoming (static) arrivals to the stop specified by number. The results from this request encode a JOIN of several tables that should provide enough information to encode a "bus". The optional "number" parameter can be used to specific a future time window in minutes. This defaults to 15 minutes. If the optional app_id and api_key parameters are set, then we'll try to look up some live data from the OC Transpo live api (http://www.octranspo1.com/developers/documentation).

- /destinations/:trip_id/:sequence[?range=:number]
  - Provides details about the upcoming stops (static) on the route identified using "trip_id" and "sequence" information obtained via a request to "/arrivals" or a previous "/destinations" request. The results from this request are in the same format as the "/arrivals" request. The optional "range" parameter can be used to control the number of upcoming stops. The default value is 10.

**NOTE**: Since this data is mined from the static schedule and since the current position of a trip is **not available** as a live feed from the provider, it requires the use of :sequence to understand where the "bus" currently appears on the route trip. Calculating a :sequence correlated to the current position of the vehicle is left as an **exercise for the reader** (hint: /stops_nearby/.../closest OR a **functioning live feed**).

Live API
--------

As of api_version 2, the API supports making raw queries of the live API. In all of these queries, api_key and app_id must be obtained from OC Transpo. We pass these through to the live API for you.

- /live/routes/:stop_id?api_key=:key&app_id=:app_id
  - Returns a list of routes *currently* serving this stop according to the live API. We assume that this might exclude trips which have been cancelled from the static schedule, but who knows?

- /live/arrivals/:stop_id/:route_no?api_key=:key&app_id=:app_id
  - Given a 4-digit stop number and a route number, this call will return live arrival times in JSON format. Timings in these results follow the same format as the static schedule. For example, the times are expressed in seconds since 00:00. This choice is so that live data can be correlated with the schedule.

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

3. "Compile" the sqlite3 database (about 5 minutes)

> thor manage:compile :sqlite_db_name :gtfs_zip_filename

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