API_VERSION = 3
SCHEMA_VERSION = 3


class Integer
  def to_json(options=nil)
    to_s
  end
end

class Fixnum
  def to_json(options=nil)
    to_s
  end
end
