# Copyright 2012 Don Kelly <karfai@gmail.com>

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

require 'sqlite3'

class Compiler
  def initialize(database_name, feed_version)
    @db = SQLite3::Database.new("#{database_name}.sqlite3")

    @db.execute('CREATE TABLE service_periods (id INTEGER PRIMARY KEY AUTOINCREMENT, days INTEGER, start TEXT, finish TEXT)')
    @db.execute('CREATE TABLE service_exceptions (id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT, exception_type INTEGER, service_period_id INTEGER)')
    @db.execute('CREATE TABLE stops (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, number INTEGER, name TEXT, lat FLOAT, lon FLOAT)')
    @db.execute('CREATE TABLE routes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, route_type INTEGER)')
    @db.execute('CREATE TABLE trips (id INTEGER PRIMARY KEY AUTOINCREMENT, headsign TEXT, block INTEGER, route_id INTEGER, service_period_id INTEGER)')
    @db.execute('CREATE TABLE pickups (id INTEGER PRIMARY KEY AUTOINCREMENT, arrival INTEGER, departure INTEGER, sequence INTEGER, trip_id INTEGER, stop_id INTEGER)')
    @db.execute('CREATE TABLE versions (id INTEGER PRIMARY KEY AUTOINCREMENT, api_version INTEGER, feed_version INTEGER)')
    @db.execute('INSERT INTO versions (api_version, feed_version) VALUES (?,?)', [1, feed_version])
    @cache = {
      :service_periods => {},
      :stops           => {},
      :routes          => {},
      :trips           => {},
    }
    @member_map = {
      'calendar'       => 'service_period',
      'calendar_dates' => 'service_exception',
      'stops'          => 'stops',
      'routes'         => 'routes',
      'trips'          => 'trips',
      'stop_times'     => 'pickups',
    }
  end

  def make_indexes()
    @db.transaction do |db|
      db.execute('CREATE INDEX idx_stop_id_pickups ON pickups (stop_id)')
      db.execute('CREATE INDEX idx_trip_id_pickups ON pickups (trip_id)')
    end
  end

  def add_service_period(vals)
    days = 0
    ['monday','tuesday','wednesday','thursday','friday','saturday','sunday'].each_with_index do |dn, idx|
      days |= vals[dn].to_i << idx
    end
    @db.execute(
        'INSERT INTO service_periods (days, start, finish) VALUES (?,?,?)',
        [days, vals['start_date'], vals['end_date']]
        )
    @cache[:service_periods][vals['service_id']] = @db.last_insert_row_id
  end

  def add_service_exception(vals)
    service_period_id = @cache[:service_periods][vals['service_id']].to_i
    exception_type = vals['exception_type'].to_i

    @db.execute(
        'INSERT INTO service_exceptions (day, exception_type, service_period_id) VALUES (?,?,?)',
        [vals['date'], exception_type, service_period_id]
        )
  end

  def add_stops(vals)
    lat = 0.0
    lon = 0.0
    
    lat = vals['stop_lat'].to_f unless 0 == vals['stop_lat'].length
    lon = vals['stop_lon'].to_f unless 0 == vals['stop_lon'].length
        
    @db.execute(
        'INSERT INTO stops (label,number,name,lat,lon) VALUES (?,?,?,?,?)',
        [vals['stop_id'], vals['stop_code'].to_i, vals['stop_name'], lat, lon,]
        )

    @cache[:stops][vals['stop_id']] = @db.last_insert_row_id
  end

  def add_routes(vals)
    rt = 0
    rt = vals['route_type'].to_i unless 0 == vals['route_type'].length

    @db.execute(
        'INSERT INTO routes (name,route_type) VALUES (?,?)',
        [vals['route_short_name'], rt,]
        )
    
    @cache[:routes][vals['route_id']] = @db.last_insert_row_id
  end

  def add_trips(vals)
    route_id = @cache[:routes][vals['route_id']].to_i
    service_period_id = @cache[:service_periods][vals['service_id']].to_i
    block = 0
    block = vals['block_id'].to_i unless 0 == vals['block_id'].length

    @db.execute(
        'INSERT INTO trips (headsign,block,service_period_id,route_id) VALUES (?,?,?,?)',
        [vals['trip_headsign'], block, service_period_id, route_id]
        )
    
    @cache[:trips][vals['trip_id']] = @db.last_insert_row_id
  end

  def time_to_secs(ts)
    (h, m, s) = ts.split(':')
    s.to_i + m.to_i * 60 + h.to_i * 3600
  end

  def add_pickups(vals)
    trip_id = @cache[:trips][vals['trip_id']]
    stop_id = @cache[:stops][vals['stop_id']]
    
    @db.execute(
        'INSERT INTO pickups (arrival, departure, sequence, trip_id, stop_id) VALUES (?,?,?,?,?)',
        [time_to_secs(vals['arrival_time']), time_to_secs(vals['departure_time']), vals['stop_sequence'].to_i, trip_id, stop_id]
        )
  end

  def add(gtfs_name, contents, progress)
    member = @member_map[gtfs_name]
    line_no = 0
    names = []
    lines = contents.split("\r\n")
    
    progress.begin(member, lines.length)

    @db.transaction do |db|
      lines.each do |l|
        if line_no > 0
          vals = {}
          l.split(',').collect { |l| l.gsub('"', '').strip }.each_with_index do |fld, idx|
            vals[names[idx]] = fld
          end
          
          send("add_#{member}", vals)
        else
          names = l.split(',')
        end

        line_no += 1
        progress.step(line_no)
      end
    end

    progress.finish()
  end
end
