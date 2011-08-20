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

import os, re, sqlite3
from datetime import *

def time_to_secs(ts):
    (h, m, s) = ts.split(':')
    return int(s) + int(m) * 60 + int(h) * 3600

def secs_to_time(secs):
    h = secs / 3600
    m = (secs % 3600) / 60
    s = (secs % 3600) % 60
    return '%02i:%02i:%02i' % (h, m, s)
    
def secs_elapsed_today():
    n = datetime.now()
    return (n - datetime(n.year, n.month, n.day)).seconds

def search_intersection(parts):
    a = unicode('%' + parts[0].upper() + '%')
    b = unicode('%' + parts[1].upper() + '%')
    return 'stops.name LIKE "%s/%s" OR stops.name LIKE "%s/%s"' % (a, b, b, a)

def search_number(parts):
    return 'stops.number=%i' % int(parts[0])

def search_label(parts):
    return 'stops.label="%s"' % unicode(parts[0].upper())

def search_any(parts):
    return 'stops.name LIKE "%s"' % unicode('%' + parts[0].upper() + '%')

srch_pats = [
    ('(\w+) and (\w+)',       search_intersection),
    ('(\w+)\s*/\s*(\w+)',     search_intersection),
    ('([0-9]{4})',            search_number),
    ('([a-zA-Z]{2}[0-9]{3})', search_label),
    ('(\w+)',                 search_any),
]

def find_search(s):
    rv = None
    for p in srch_pats:
        mt = re.match(p[0], s)
        if mt:
            rv = p[1](mt.groups())
            
            if rv:
                break
            
    return rv

class ORM(object):
    def __init__(self, dbf):
        self._conn = sqlite3.connect(dbf)

    def update(self, tbl, id, fields):
        fl = ','.join(['%s=:%s' % (n, n) for n in fields])
        q = 'UPDATE %s SET %s WHERE id=%s' % (tbl, fl, id)

        c = self._conn.cursor()
        c.execute(q, fields)
        c.close()

    def commit(self):
        self._conn.commit()        

    def find_one(self, klass, q, args):
        c = self._conn.cursor()
        c.execute(q, args)
        r = c.fetchone()
        rv = None
        if r:
            rv = klass(self, *r)
        c.close()
        return rv

    def find_many(self, klass, q, args={}):
        c = self._conn.cursor()
        c.execute(q, args)
        rv = [klass(self, *r) for r in c.fetchall()]
        c.close()
        return rv
        
    def find_and_filter_one(self, klass, q, args, fn):
        rv = None
        l = [o for o in self.find_many(klass, q, args) if fn(o)]
        if len(l) > 0:
            rv = l[0]
        return rv

    def cursor(self):
        return self._conn.cursor()

class Routing(ORM):
    def __init__(self, dbf='transit.db'):
        super(Routing, self).__init__(dbf)

    def current_time(self):
        return datetime.now()

    def current_service_period(self):
        n = self.current_time()
        fl = (1 << n.weekday())
        day = n.date()
        ex = self.find_service_exception(day.strftime('%Y%m%d'))
        rv = None
        if ex:
            rv = ex.service_period()
        else:
            rv = self.find_and_filter_one(ServicePeriod,
                                           'SELECT * FROM service_periods',
                                           { },
                                           lambda sp : sp.days & fl and sp.in_service(day))
        return rv

    def get_stop_number_stat(self):
        rv = [0, 0]
        for st in self.find_all_stops():
            if st.number == 0:
                rv[1] += 1
            else:
                rv[0] += 1
        return rv

    def find_service_exception(self, day):
        return self.find_one(ServiceException,
                             'SELECT * FROM service_exceptions WHERE service_exceptions.day=:day',
                             { 'day' : day})
    
    def find_stop(self, stop_id):
        return self.find_one(Stop,
                             'SELECT * FROM stops WHERE stops.id=:id',
                             { 'id' : stop_id})

    def find_all_stops(self):
        return self.find_many(Stop,
                             'SELECT * FROM stops',
                             {})

    def find_stop_by_number(self, num):
        return self.find_one(Stop,
                             'SELECT * FROM stops WHERE stops.number=:number',
                             { 'number' : num})

    def find_stop_by_label(self, num):
        return self.find_one(Stop,
                             'SELECT * FROM stops WHERE stops.label=:label',
                             { 'label' : num})

    def find_trip(self, trip_id):
        return self.find_one(Trip,
                             'SELECT * FROM trips WHERE trips.id=:id',
                             { 'id' : trip_id})

    def stop_search(self, ss):
        wh = find_search(ss)
        rv = []
        if wh:
            rv = self.find_many(Stop,
                                'SELECT stops.* FROM stops WHERE %s' % (wh))
        return rv

class Local(ORM):
    def __init__(self):
        super(Local, self).__init__('local.db')

    def make(self):
        cur = self.cursor()
        cur.execute('CREATE TABLE searches (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT)')
        self.commit()
        cur.close()

    def searches(self):
        return self.find_many(Search,
                              'SELECT * FROM searches',
                              {})

    def have_search(self, text):
        s = self.find_one(Search,
                          'SELECT * FROM searches WHERE text=:text',
                          { 'text' : text})
        return s is not None

    def save_search(self, text):
        if not self.have_search(text):
            cur = self.cursor()
            cur.execute('INSERT INTO searches (text) VALUES (?)', [text,])
            self.commit()
            cur.close()

def local():
    exists = os.path.exists('local.db')
    rv = Local()
    if not exists:
        rv.make()
    return rv

class SObject(object):
    def __init__(self, orm, id):
        self.orm = orm
        self.id = id

    def update(self):
        self.orm.update(self.table(), self.id, self.fields())

class Search(SObject):
    def __init__(self, orm, id, text):
        super(Search, self).__init__(orm, id)
        self.text = text

class ServicePeriod(SObject):
    def __init__(self, orm, id, days, start, finish):
        super(ServicePeriod, self).__init__(orm, id)

        self.days = days
        self.start = start
        self.finish = finish

    def in_service(self, dt):
        st = datetime.strptime(self.start, '%Y%m%d').toordinal()
        en = datetime.strptime(self.finish, '%Y%m%d').toordinal()
        return dt.toordinal() >= st and dt.toordinal() <= en
    
class ServiceException(SObject):
    def __init__(self, orm, id, day, exception_type, service_period_id):
        super(ServiceException, self).__init__(orm, id)

        self.day = day
        self.exception_type = exception_type
        self.service_period_id = service_period_id

    def service_period(self):
        return self.orm.find_one(ServicePeriod,
                                'SELECT * FROM service_periods WHERE id=:id',
                                { 'id' : self.service_period_id})

class Pickup(SObject):
    def __init__(self, orm, id, arrival, departure, sequence, trip_id, stop_id):
        super(Pickup, self).__init__(orm, id)
        self.arrival = arrival
        self.departure = departure
        self.sequence = sequence
        self.trip_id = trip_id
        self.stop_id = stop_id

    def arrival_s(self):
        return secs_to_time(self.arrival)

    def in_service(self, service_period):
        return self.trip().in_service(service_period)

    def arrives_in_range(self, r):
        return self.arrival in r

    def is_last(self):
        return 0 == len(self.trip().next_pickups_from_pickup(self, 1))

    def minutes_until_arrival(self):
        n = secs_elapsed_today()
        return (self.arrival - n) / 60
    
    def trip(self):
        return self.orm.find_trip(self.trip_id)

    def stop(self):
        return self.orm.find_stop(self.stop_id)

class Stop(SObject):
    def __init__(self, orm, id, label, number, name, lat, lon):
        super(Stop, self).__init__(orm, id)
        self.label = label
        self.number = number
        self.name = name
        self.lat = lat
        self.lon = lon

    def table(self):
        return 'stops'

    def fields(self):
        return {
            'label' : self.label,
            'number' : self.number,
            'name' : self.name,
            'lat' : self.lat,
            'lon' : self.lon,
        }
    def upcoming_pickups(self, offset):
        t = secs_elapsed_today()
        r = range(t - 5 * 60, (t + offset * 60) + 1)
        sp = self.orm.current_service_period()
        rv = [pu for pu in self.pickups() if pu.in_service(sp) and pu.arrives_in_range(r)]
        rv.sort(cmp=lambda a,b: cmp(a.arrival, b.arrival))
        return rv

    def trips(self):
        return self.orm.find_many(Trip,
                                 'SELECT trips.* FROM trips,pickups WHERE trips.id=pickups.trip_id AND pickups.stop_id=:id',
                                 { 'id' : self.id})

    def pickups(self):
        return self.orm.find_many(Pickup,
                                 'SELECT * FROM pickups WHERE pickups.stop_id=:id',
                                 { 'id' : self.id})
        
class Route(SObject):
    def __init__(self, orm, id, name, ty):
        super(Route, self).__init__(orm, id)
        self.name = name
        self.type = ty

    def trips(self):
        return self.orm.find_many(Trip,
                                 'SELECT * FROM trips WHERE trips.route_id=:id',
                                 { 'id' : self.id})

class Trip(SObject):
    def __init__(self, orm, id, headsign, block, route_id, service_period_id):
        super(Trip, self).__init__(orm, id)

        self.headsign = headsign
        self.block = block
        self.route_id = route_id
        self.service_period_id = service_period_id

    def in_service(self, service_period):
        return self.service_period_id == service_period.id

    def _pickups_in_sequence(self):
        rv = [pu for pu in self.pickups()]
        rv.sort(cmp=lambda a,b: cmp(a.sequence, b.sequence))
        return rv

    def next_pickups_from_now(self, limit, offset=0):
        tm = secs_elapsed_today() - offset
        return [pu for pu in self._pickups_in_sequence() if pu.arrival >= tm][0:limit]

    def next_pickups_from_pickup(self, stpu, limit):
        return [pu for pu in self._pickups_in_sequence() if pu.sequence > stpu.sequence][0:limit]

    def route(self):
        return self.orm.find_one(Route,
                                'SELECT * FROM routes WHERE id=:id',
                                { 'id' : self.route_id})

    def service_period(self):
        return self.orm.find_one(ServicePeriod,
                                'SELECT * FROM service_periods WHERE id=:id',
                                { 'id' : self.service_period_id})

    def stops(self):
        return self.orm.find_many(Stop,
                                 'SELECT stops.* FROM stops,pickups WHERE stops.id=pickups.stop_id AND pickups.trip_id=:id',
                                 { 'id' : self.id})

    def pickups(self):
        return self.orm.find_many(Pickup,
                                 'SELECT * FROM pickups WHERE pickups.trip_id=:trip_id',
                                 { 'trip_id' : self.id})
    
def make(dbf='transit.db'):
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


