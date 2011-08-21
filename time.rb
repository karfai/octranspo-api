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
