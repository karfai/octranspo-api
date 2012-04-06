require 'faraday'
require 'nokogiri'

require './time'

class Hash
  def join(inner=$,, outer=$,)
    map { |e| e.join(inner) }.join(outer)
  end
end

class Live
  def initialize(app_id, api_key)
    @app_id = app_id
    @api_key = api_key
    @conn = Faraday.new('https://api.octranspo1.com')
    @mappings = {
      :next_for_route => {
        'TripDestination'     => { :key => :destination, :conv => lambda { |s| s } },
        'TripStartTime'       => { :key => :departure_from_origin, :conv => lambda { |s| hour_and_minutes_to_elapsed(s) } },
        'AdjustedScheduleTime'=> { :key => :expected, :conv => lambda { |s| secs_elapsed_today + 60 * s.to_i } },
        'AdjustmentAge'       => { :key => :age, :conv => lambda { |s| '-1' == s ? nil : (s.to_f * 60).to_i } },
        'BusType'             => { :key => :bus_type, :conv => lambda { |s| s } },
        'Latitude'            => { :key => :latitude, :conv => lambda { |s| s.to_f } },
        'Longitude'           => { :key => :longitude, :conv => lambda { |s| s.to_f } },
        'GPSSpeed'            => { :key => :approximate_speed, :conv => lambda { |s| s.to_f } },
      }
    }
  end

  def update_pickups(stop_no, pickups)
    adjustments = {}
    counters = {}

    # this is complicated b/c our pickups only contain a time window
    # the remote live call gives us much more. therefore we try to 
    # merge the results into the original pickups. we assume that we're
    # getting the results from the live system in the same order
    # as those in the pickups array
    pickups.collect { |v| v[:trip][:route] }.uniq.each do |route_no|
      next_for_route(stop_no, route_no) do |vals|
        adjustments[route_no] = vals
        counters[route_no] = 0
      end
    end

    pickups.collect do |old_vals|
      vals = old_vals.clone
      route_no = vals[:trip][:route]
      live = adjustments[route_no][counters[route_no]]
      vals[:arrival_difference] = vals[:arrival] - live[:expected]
      vals[:scheduled_arrival] = vals[:arrival]
      vals[:arrival] = live[:expected]
      vals[:live] = {
        :departure_from_origin => live[:departure_from_origin],
        :age                   => live[:age],
        :location              => {
          :lat                   => live[:latitude],
          :lon                   => live[:longitude],
          :approximate_speed     => live[:approximate_speed],
        },
      }

      counters[route_no] += 1
      vals
    end if adjustments.length
  end

  def request(op, root, payload)
    payload['appID'] = @app_id
    payload['apiKey'] = @api_key

    resp = @conn.post("/#{op}", payload.join('=', '&'))
    yield(Nokogiri::XML(resp.body).css(root))
  end

  def next_for_route(stop_no, route_no)
    request('GetNextTripsForStop', 'GetNextTripsForStopResult', { 'stopNo' => stop_no, 'routeNo' => route_no }) do |root_node|
      arr = root_node.css('Trips/Trip/node').collect do |pn|
        vals = { :stop_no => stop_no, :route_no => route_no }
        @mappings[:next_for_route].each do |k, v|
          n = pn.css(k.to_s)
          vals[v[:key].to_sym] = v[:conv].call(n.first.content) if n
        end
        vals
      end
      yield(arr)
    end
  end
end
