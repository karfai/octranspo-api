require 'date'
require 'tzinfo'

$ltz = TZInfo::Timezone.get('America/Montreal')

def now()
  p "NOW"
  p $ltz.utc_to_local(Time.now.utc)
  $ltz.utc_to_local(Time.now.utc)
end

def today()
  $ltz.utc_to_local(Date.today.to_time.utc)
end

def secs_elapsed_today
  (now - today).to_i
end

def time_window_on_elapsed(secs)
  el = secs_elapsed_today
  [el, el + secs] 
end
