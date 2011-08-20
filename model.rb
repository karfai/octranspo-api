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

require 'data_mapper'
require 'date'

def secs_elapsed_today
  (Time.now - Date.today.to_time).to_i
end

def time_window_on_elapsed(secs)
  el = secs_elapsed_today
  [el, el + secs] 
end

# If you want the logs displayed you have to do this before the call to setup
DataMapper::Logger.new($stdout, :debug)
DataMapper.setup(:default, 'sqlite:///home/don/src/projects/octranspo/octranspo-api/octranspo.sqlite3')

class ServicePeriod
  include DataMapper::Resource

  property :id,     Serial
  property :days,   Integer
  property :start,  String
  property :finish, String

  has n,   :trips

  def self.current(&bl)
    dt = Date.today
    dts = dt.strftime('%Y%m%d')

    sp = nil
    ex = ServiceException.first(:day => dts)
    if ex
      sp = ex.service_period
    else
      sp = all(:start.lte => dts, :finish.gte => dts).select do |spi|
        spi.match_date_in_days(dt)
      end.first
    end

    if bl
      bl.call(sp)
    end

    sp
  end

  def contains_day_ordinal(d)
    (days & (1 << d)) > 0
  end

  def match_date_in_days(dt)
    # moday == 0 i/t feed
    contains_day_ordinal(dt.wday == 0 ? 6 : dt.wday - 1)
  end

  def days_in_service()
    i = 0
    [:mon, :tue, :wed, :thu, :fri, :sat, :sun].select do |d|
      matches = contains_day_ordinal(i)
      i += 1
      matches
    end
  end

  def humanize()
    vals = {}
    vals[:id] = id
    vals[:start] = start
    vals[:finish] = finish
    i = 0
    vals[:days] = days_in_service
    vals
  end
end

class ServiceException
  include DataMapper::Resource

  property   :id,             Serial
  property   :day,            String
  property   :exception_type, Integer

  belongs_to :service_period
end

class Trip
  include DataMapper::Resource

  property :id,     Serial
  property :headsign, String

  belongs_to :service_period
  belongs_to :route

  has n,     :pickups
end

class Route
  include DataMapper::Resource

  property :id,   Serial
  property :name, String

  has n,   :trips
end

class Stop
  include DataMapper::Resource

  property :id,     Serial
  property :label,  String
  property :number, Integer
  property :name,   String
  property :lat,    Float
  property :lon,    Float

  has n,   :pickups
end

class Pickup
  include DataMapper::Resource

  property :id,        Serial
  property :arrival,   Integer
  property :departure, Integer
  property :sequence,  Integer
  property :trip_id,   Integer

  belongs_to :trip
  belongs_to :stop

  def self.pickups_at_stop_in_range(stop_number, range)
    rv = []
    ServicePeriod.current do |sp|
      rv = Stop.first(:number => stop_number).pickups.all(:arrival.gte => range[0], :arrival.lte => range[1], :order => [:arrival.asc]).select do |pi|
        pi.trip.service_period_id == sp.id
      end
    end

    rv
  end

  def self.arriving_at_stop(stop_number, minutes)
    pickups_at_stop_in_range(stop_number, time_window_on_elapsed(minutes * 60))
  end

  def next_in_sequence(range)
    Pickup.all(:trip_id => trip_id, :sequence.gt => sequence, :sequence.lte => sequence + range)
  end

  def humanize()
    {
      :stop      => { :number => stop.number, :name => stop.name },
      :trip      => { :id => trip.id, :route => trip.route.name, :headsign => trip.headsign },
      :arrival   => arrival,
      :departure => departure,
      :sequence  => sequence,
    }
  end
end

DataMapper.finalize
