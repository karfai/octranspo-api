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
require 'sinatra'

require './time'

# DataMapper::Logger.new($stdout, :debug)
DataMapper.setup(:default, ENV['DATABASE_URL'] || 'postgres://localhost/octranspo')
configure :test do
  DataMapper.setup(:default, 'sqlite::memory:')
end

class ServicePeriod
  include DataMapper::Resource

  property :id,     Serial
  property :days,   Integer
  property :start,  String
  property :finish, String

  has n,   :trips

  def in_service?(dt=nil)
    # NOTE: don't check exceptions -- this ServicePeriod is valid
    # $today of it's own right
    dt = Date.today if not dt
    dts = dt.strftime('%Y%m%d')
    start <= dts && finish >= dts && match_date_in_days(dt)
  end

  def self.day_names()
    [:mon, :tue, :wed, :thu, :fri, :sat, :sun]
  end

  def contains_day_ordinal(d)
    (days & (1 << d)) > 0
  end

  def match_date_in_days(dt)
    # monday == 0 i/t feed
    contains_day_ordinal(dt.wday == 0 ? 6 : dt.wday - 1)
  end

  def days_in_service()
    i = 0
    ServicePeriod.day_names.select do |d|
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
    vals[:days] = days_in_service
    vals
  end

  def to_s
    "#{id}: [#{start} => #{finish}]: #{days_in_service}"
  end
end

# TODO: figure out what to do with ServiceExceptions. now that we always
# use ServicePeriod.in_service? do we really need to check otherwise?
# TODO: related to above: maybe some routes have sp:id0, normally, but use
# exceptions to remove service at certain times? this would mean that we need to
# check the exception_type
class ServiceException
  include DataMapper::Resource

  property   :id,             Serial
  property   :day,            String
  property   :exception_type, Integer

  belongs_to :service_period

  def addition?()
    1 == exception_type
  end

  def reduction?()
    2 == exception_type
  end
end

class Trip
  include DataMapper::Resource

  property :id,       Serial
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

  def collect_pickup_services(in_service)
    services = {}
    pickups.each do |pi|
      tr = pi.trip
      if !in_service || (in_service && tr.service_period.in_service?)
        rt = "#{tr.route.name} #{tr.headsign}"
        services[rt] = { :arrivals => [], :route => { :number => tr.route.name, :headsign => tr.headsign }, :service_periods => {} } if !services.key?(rt)
        services[rt][:arrivals] << pi.arrival
        services[rt][:service_periods][tr.service_period_id] = 1
      end
    end

    services
  end

  def collate_pickup_services(services)
    collated = {}
    services.each do |k, v|
      days = []
      v[:service_periods].each do |id, v|
        sp = ServicePeriod.get(id)
        days = days + sp.days_in_service
      end
      collated[k] = {
        :route => v[:route],
        :arrivals => v[:arrivals].sort,
        :days  => days.uniq,
      }
    end

    collated
  end

  def routes(in_service)
    collate_pickup_services(collect_pickup_services(in_service)).values
  end

  private :collate_pickup_services, :collect_pickup_services
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

  def self.pickups_at_stop_in_range(stop_number, range, dt=nil)
    Stop.first(:number => stop_number).pickups.all(
      :arrival.gte => range[0],
      :arrival.lte => range[1],
      :order => [:arrival.asc]).select do |pi|
        pi.trip.service_period.in_service? dt
    end
  end

  def self.arriving_at_stop(stop_number, minutes, dt=nil, seconds_since_midnight=nil)
    window_secs = minutes * 60
    range = time_window_on_elapsed(window_secs)
    range = [seconds_since_midnight, seconds_since_midnight + window_secs] if seconds_since_midnight
    pickups_at_stop_in_range(stop_number, range, dt)
  end

  def next_in_sequence(range)
    Pickup.all(:trip_id => trip_id, :sequence.gt => sequence, :sequence.lte => sequence + range, :order => [:sequence])
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

class Version
  include DataMapper::Resource

  property :id,             Serial
  property :schema_version, Integer
  property :feed_version,   Integer
end

DataMapper.finalize
