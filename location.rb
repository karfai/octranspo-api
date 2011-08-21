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

require 'geokit'

require './model'

def measure_distance(st, pt0)
  pt1 = Geokit::LatLng.new(st.lat, st.lon)
  pt0.distance_to(pt1, { :units => :kms }) * 1000.0
end

def measure_all_stops(pt0, ignore)
  Stop.all.each do |st|
    if st.id != ignore
      yield(measure_distance(st, pt0), st)
    end
  end  
end

def nearby_point(pt0, distance_in_meters, ignore=0)
  matches = []
  measure_all_stops(pt0, ignore) do |dist_to, st|
    matches << { :distance => dist_to.to_i, :stop => st } if dist_to <= distance_in_meters
  end

  matches.sort { |a, b| a[:distance] <=> b[:distance] }
end

def closest_point(pt0, ignore=0)
  rv = nil

  measure_all_stops(pt0, ignore) do |dist_to, st|
    rv = { :distance => dist_to.to_i, :stop => st } if !rv || dist_to < rv[:distance]
  end

  [rv]
end

def select_nearby_method(lat, lon, distance_in_meters)
  pt = Geokit::LatLng.new(lat, lon)
  (distance_in_meters > 0) ? nearby_point(pt, distance_in_meters, id) : closest_point(pt, id)
end

class Stop
  def nearby(distance_in_meters=0)
    select_nearby_method(lat, lon, distance_in_meters)
  end

  def self.nearby(lat, lon, distance_in_meters=0)
    select_nearby_method(lat, lon, distance_in_meters)
  end
end

class Coords
  def initialize(lat, lon)
    @lat = lat
    @lon = lon
  end

  def nearby(meters=0)
    Stop.nearby(@lat, @lon, meters)
  end
end
