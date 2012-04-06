require 'date'
require 'tzinfo'

$ltz = TZInfo::Timezone.get('America/Montreal')

def now()
  $ltz.utc_to_local(Time.now.utc)
end

def today()
  dt = Date.today
  Time.new(dt.year, dt.mon, dt.day, 0, 0, 0, 0)
end

def secs_elapsed_today
  (now - today).to_i
end

def time_window_on_elapsed(secs)
  el = secs_elapsed_today
  [el, el + secs] 
end

def hour_and_minutes_to_elapsed(s)
  p = s.split(':')
  p[0].to_i * 3600 + p[1].to_i * 60
end
