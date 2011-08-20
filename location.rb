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

def nearby_point(pt0, distance_in_meters)
  kms = distance_in_meters / 1000.0

  Stop.all.select do |st|
    pt1 = Geokit::LatLng.new(st.lat, st.lon)
    pt0.distance_to(pt1, { :units => :kms }) <= kms
  end
end

class Stop
  def nearby(distance_in_meters)
    nearby_point(Geokit::LatLng.new(lat, lon), distance_in_meters)
  end

  def self.nearby(lat, lon, distance_in_meters)
    nearby_point(Geokit::LatLng.new(lat, lon), distance_in_meters)
  end

  private :nearby_point
end
