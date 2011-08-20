# Copyright 2009 Don Kelly <karfai@gmail.com>

# This file is part of voyageur.

# voyageur is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# voyageur is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with voyageur.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement

import curses.wrapper
import dateutil.parser
import lxml.etree
import os
import schema
import sys
import urllib2
import zipfile
from datetime import *

def add_stop(cur, cache, parts):
    lat = 0.0
    lon = 0.9
    if not 0 == len(parts[4]):
        lat = float(parts[4])
    if not 0 == len(parts[5]):
        lat = float(parts[5])
        
    cur.execute(
        'INSERT INTO stops (label,number,name,lat,lon) VALUES (?,?,?,?,?)',
        [parts[0], parts[1], parts[2], lat, lon,]
        )
    cache['stops'][parts[0]] = cur.lastrowid

def add_route(cur, cache, parts):
    rt = 0
    if not 0 == len(parts[4]):
        rt = int(parts[4])
    cur.execute(
        'INSERT INTO routes (name,route_type) VALUES (?,?)',
        [parts[1], rt,]
        )
    
    cache['routes'][parts[0]] = cur.lastrowid

def add_trip(cur, cache, parts):
    route_id = cache['routes'][parts[0]]
    service_period_id = cache['service_periods'][parts[1]]
    block = 0
    if not 0 == len(parts[4]):
        block = int(parts[4])
    cur.execute(
        'INSERT INTO trips (headsign,block,service_period_id,route_id) VALUES (?,?,?,?)',
        [parts[3], block, service_period_id, route_id]
        )
    
    cache['trips'][parts[2]] = cur.lastrowid

def add_pickup(cur, cache, parts):
    trip_id = cache['trips'][parts[0]]
    stop_id = cache['stops'][parts[3]]

    cur.execute(
        'INSERT INTO pickups (arrival, departure, sequence, trip_id, stop_id) VALUES (?,?,?,?,?)',
        [schema.time_to_secs(parts[1]), schema.time_to_secs(parts[2]), int(parts[4]), trip_id, stop_id]
        )

def add_service_period(cur, cache, parts):
    p = 0
    days = 0
    for i in parts[1:8]:
        days |= (int(i) << p)
        p += 1
    cur.execute(
        'INSERT INTO service_periods (days, start, finish) VALUES (?,?,?)',
        [days, parts[8], parts[9]]
        )
    cache['service_periods'][parts[0]] = cur.lastrowid

def add_service_exception(cur, cache, parts):
    service_period_id = cache['service_periods'][parts[0]]
    exception_type = int(parts[2])
    cur.execute(
        'INSERT INTO service_exceptions (day, exception_type, service_period_id) VALUES (?,?,?)',
        [parts[1], exception_type, service_period_id]
        )

class Msgs:
    def __init__(self, w):
        self._w = w
        self._y = 0

    def show(self, m):
        self._w.addstr(self._y, 0, m, curses.A_BOLD)
        self._w.clrtoeol()
        self._w.refresh()
        self.next_line()

    def show_step(self, m, inc=True):
        self._w.addstr(self._y, 2, '+ %s' % (m))
        self._w.clrtoeol()
        self._w.refresh()
        if inc:
            self.next_line()

    def next_line(self):
        self._y += 1

class Builder:  
    def __init__(self, conn, msg):
        self._conn = conn
        self._msg = msg
        self._cache = {
            'stops'  : {},
            'service_periods'  : {},
            'routes' : {},
            'trips'  : {}
        }

    def build(self, fuel):
        (t, fn) = fuel
       
        with open('feed/%s.txt' % (t)) as f:
            skip_one = True
            lines = f.readlines()
            tlc = len(lines)
            lc = 0

            for ln in lines:
                if not skip_one:
                    self._msg.show_step('%s %i/%i' % (t.ljust(15), lc + 1, tlc), False)
                    parts = [p.replace('"', '').strip() for p in unicode(ln.rstrip(), 'utf_8').split(',')]
                    cur = self._conn.cursor()
                    fn(cur, self._cache, parts)
                    cur.close()
                else:
                    skip_one = False
                lc += 1
            self._msg.next_line()
        self._conn.commit()

builders = [
    ['calendar',       add_service_period],
    ['calendar_dates', add_service_exception],
    ['stops',          add_stop],
    ['routes',         add_route],
    ['trips',          add_trip],
    ['stop_times',     add_pickup],
]

class StopUpdate:
    def __init__(self, msg, tot):
        self.m = 0
        self._msg = msg
        self._tot = tot
        self._cur = 1

    def update_stop(self, sch, in_id, ph_id, name):
        stop = sch.find_stop_by_label(in_id)
        if not stop:
            self._msg.show_step('not found: %s (%i/%i)' % (in_id, self._cur, self._tot), False)
            self.m += 1
        else:
            self._msg.show_step('updating: %s (%i/%i)' % (in_id, self._cur, self._tot), False)
            stop.number = int(ph_id)
            stop.update()
        self._cur += 1

def inject_stops(xfl, fl, msg):
    msg.show('Injecting stop numbers from stops.xml')
    sch = schema.Routing(fl)

    msg.show_step('parsing %s' % (xfl))
    tr = lxml.etree.parse(xfl)
    elems = tr.xpath('/stops/marker')

    upd = StopUpdate(msg, len(elems))
    [upd.update_stop(sch, e.get('stopid'), e.get('id'), e.get('name')) for e in elems]
    sch.commit()    

def extract_member(z, mfl, msg):
    msg.show_step(mfl)
    z.extract(mfl, 'feed')

def extract_feed(fl, msg):
    msg.show('Extracting GTFS feed from %s' % (fl))
    z = zipfile.ZipFile(fl, 'r')
#    members = ['agency.txt', 'calendar_dates.txt', 'calendar.txt', 'error.txt', 'routes.txt', 'stops.txt', 'stop_times.txt', 'trips.txt']
    members = ['agency.txt', 'calendar_dates.txt', 'calendar.txt', 'routes.txt', 'stops.txt', 'stop_times.txt', 'trips.txt']
    [extract_member(z, m, msg) for m in members]

def download_latest(msg):
    surl = 'http://www.gtfs-data-exchange.com/agency/oc-transpo/latest.zip'
    msg.show('Retrieving latest GTFS feed (%s)' % (surl))

    fn = '/tmp/octranspo.zip'
    with open(fn, 'w') as f:
        f.write(urllib2.urlopen(surl).read())
    return fn

def run(ss, ofl, zfl):
    msg = Msgs(ss)
    if os.path.exists(ofl):
        os.unlink(ofl)
    
    rm_zfl = False
    if zfl is None:
        zfl = download_latest(msg)
        rm_zfl = True
    extract_feed(zfl, msg)
    if rm_zfl:
        os.unlink(zfl)

    msg.show('Creating database in %s' % (ofl))
    conn = schema.make(ofl)

    msg.show('Converting GTFS feed to sqlite')    

    b = Builder(conn, msg)
    [b.build(fuel) for fuel in builders]

    msg.show('Building indexes')
    schema.make_indexes(conn)

#    inject_stops('stops.xml', ofl, msg)
    msg.next_line()

ofl = 'transit.db'
zfl = None
if len(sys.argv) > 1:
    ofl = sys.argv[1]

if len(sys.argv) > 2:
    zfl = sys.argv[2]

curses.wrapper(run, ofl, zfl)

