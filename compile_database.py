# Copyright 2011 Don Kelly <karfai@gmail.com>

# This file is part of octranspo-api.

# octranspo-api is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# octranspo-api is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with octranspo-api.  If not, see <http://www.gnu.org/licenses/>.

# TODO discontinue curses use

from __future__ import with_statement

import curses.wrapper
import dateutil.parser
import lxml.etree
import os
import sqlite3
import sys
import urllib2
import zipfile
from datetime import *

def make_schema(dbf):
    conn = sqlite3.connect(dbf)
    cur = conn.cursor()
    cur.execute('CREATE TABLE stops (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, number INTEGER, name TEXT, lat FLOAT, lon FLOAT)')
    cur.execute('CREATE TABLE routes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, route_type INTEGER)')
    cur.execute('CREATE TABLE trips (id INTEGER PRIMARY KEY AUTOINCREMENT, headsign TEXT, block INTEGER, route_id INTEGER, service_period_id INTEGER)')
    cur.execute('CREATE TABLE pickups (id INTEGER PRIMARY KEY AUTOINCREMENT, arrival INTEGER, departure INTEGER, sequence INTEGER, trip_id INTEGER, stop_id INTEGER)')
    cur.execute('CREATE TABLE service_periods (id INTEGER PRIMARY KEY AUTOINCREMENT, days INTEGER, start TEXT, finish TEXT)')
    cur.execute('CREATE TABLE service_exceptions (id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT, exception_type INTEGER, service_period_id INTEGER)')
    # android "specialness"
    cur.execute('CREATE TABLE android_metadata (locale TEXT)')
    cur.execute('INSERT INTO android_metadata (locale) VALUES ("ld_US");');
    conn.commit()
    cur.close()
    return conn

def make_indexes(conn):
    cur = conn.cursor()
    cur.execute('CREATE INDEX idx_stop_id_pickups ON pickups (stop_id)')
    cur.execute('CREATE INDEX idx_trip_id_pickups ON pickups (trip_id)')
    conn.commit()
    cur.close()

def time_to_secs(ts):
    (h, m, s) = ts.split(':')
    return int(s) + int(m) * 60 + int(h) * 3600

def add_stop(cur, cache, parts):
    lat = 0.0
    lon = 0.0
    if not 0 == len(parts['stop_lat']):
        lat = float(parts['stop_lat'])
    if not 0 == len(parts['stop_lon']):
        lon = float(parts['stop_lon'])
        
    cur.execute(
        'INSERT INTO stops (label,number,name,lat,lon) VALUES (?,?,?,?,?)',
        [parts['stop_id'], parts['stop_code'], parts['stop_name'], lat, lon,]
        )
    cache['stops'][parts['stop_id']] = cur.lastrowid

def add_route(cur, cache, parts):
    rt = 0
    if not 0 == len(parts['route_type']):
        rt = int(parts['route_type'])
    cur.execute(
        'INSERT INTO routes (name,route_type) VALUES (?,?)',
        [parts['route_short_name'], rt,]
        )
    
    cache['routes'][parts['route_id']] = cur.lastrowid

def add_trip(cur, cache, parts):
    route_id = cache['routes'][parts['route_id']]
    service_period_id = cache['service_periods'][parts['service_id']]
    block = 0
    if not 0 == len(parts['block_id']):
        block = int(parts['block_id'])
    cur.execute(
        'INSERT INTO trips (headsign,block,service_period_id,route_id) VALUES (?,?,?,?)',
        [parts['trip_headsign'], block, service_period_id, route_id]
        )
    
    cache['trips'][parts['trip_id']] = cur.lastrowid

def add_pickup(cur, cache, parts):
    trip_id = cache['trips'][parts['trip_id']]
    stop_id = cache['stops'][parts['stop_id']]

    cur.execute(
        'INSERT INTO pickups (arrival, departure, sequence, trip_id, stop_id) VALUES (?,?,?,?,?)',
        [time_to_secs(parts['arrival_time']), time_to_secs(parts['departure_time']), int(parts['stop_sequence']), trip_id, stop_id]
        )

def add_service_period(cur, cache, parts):
    p = 0
    days = 0
    names = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
    for k in names:
        days |= (int(parts[k]) << p)
        p += 1
    cur.execute(
        'INSERT INTO service_periods (days, start, finish) VALUES (?,?,?)',
        [days, parts['start_date'], parts['end_date']]
        )
    cache['service_periods'][parts['service_id']] = cur.lastrowid

def add_service_exception(cur, cache, parts):
    service_period_id = cache['service_periods'][parts['service_id']]
    exception_type = int(parts['exception_type'])
    cur.execute(
        'INSERT INTO service_exceptions (day, exception_type, service_period_id) VALUES (?,?,?)',
        [parts['date'], exception_type, service_period_id]
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

        lf = open('log.txt', 'w')
        
        with open('feed/%s.txt' % (t)) as f:
            lines = f.readlines()
            tlc = len(lines)
            lc = 1
            flds = lines[0].strip().split(',')
            print >>lf, flds
            for ln in lines[1:]:
                self._msg.show_step('%s %i/%i' % (t.ljust(15), lc + 1, tlc), False)
                raw_parts = [p.replace('"', '').strip() for p in unicode(ln.rstrip(), 'utf_8').split(',')]
                cur = self._conn.cursor()
                parts = {}
                for i in range(0, len(flds)):
                    parts[flds[i]] = raw_parts[i]
                print >>lf, parts
                fn(cur, self._cache, parts)
                cur.close()
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
    conn = make_schema(ofl)

    msg.show('Converting GTFS feed to sqlite')    

    b = Builder(conn, msg)
    [b.build(fuel) for fuel in builders]

    msg.show('Building indexes')
    make_indexes(conn)

    msg.next_line()

ofl = 'transit.db'
zfl = None
if len(sys.argv) > 1:
    ofl = sys.argv[1]

if len(sys.argv) > 2:
    zfl = sys.argv[2]

curses.wrapper(run, ofl, zfl)

