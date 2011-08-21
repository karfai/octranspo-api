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

require './model'
require './location'

st = Stop.first(:number => 3011)
services = {}
st.pickups.each do |pi|
  tr = pi.trip
  rt = "#{tr.route.name} #{tr.headsign}"
  services[rt] = { :trips => [], :route => { :number => tr.route.name, :headsign => tr.headsign }, :service_periods => {} } if !services.key?(rt)
  services[rt][:trips] << tr.id
  services[rt][:service_periods][tr.service_period_id] = 1
end

services_human = {}
services.each do |k, v|
  days = []
  v[:service_periods].each do |id, v|
    sp = ServicePeriod.get(id)
    days = days + sp.days_in_service
  end
  services_human[k] = {
    :route => v[:route],
    :trips => v[:trips],
    :days  => days.uniq,
  }
end

p services_human
