require 'rspec'
require 'date'

require './model'
require File.dirname(__FILE__) + '/spec_helper'

describe ServicePeriod do
  before(:all) do
    DataMapper.auto_migrate!
    [
     [1, '20120326', '20120420', 31],
     [2, '20120331', '20120421', 32],
     [3, '20120401', '20120415', 64],
     [4, '20120409', '20120409', 31],
     [5, '20120422', '20120617', 64],
     [6, '20120423', '20120622', 31],
     [7, '20120428', '20120623', 32],
     [8, '20120326', '20120416', 1],
     [9, '20120327', '20120417', 2],
    ].each do |vals|
      ServicePeriod.create(
        :id => vals[0],
        :start => vals[1],
        :finish => vals[2],
        :days => vals[3])
    end
  end

  it 'should indicate whether it applies to a given date' do
    # a sample of service periods in the test fuel
    checks = {
      # 20120326 - 20120420 mon-fri
      1 => [['20120329', '20120403', '20120419'], ['20120421', '20120423', '20120323', '20120407']],
      # 20120331 - 20120421 sat
      2 => [['20120407', '20120421'], ['20120420', '20120422', '20120405']],
      # 20120401 - 20120415 sun
      3 => [['20120401', '20120408'], ['20120402', '20120331']],
      # 20120409 - 20120409 mon-fri
      4 => [['20120409'], ['20120410', '20120408']],
      # 20120422 - 20120617 sun
      5 => [['20120429', '20120603'], ['20120602', '20120605', '20120524']],
      # 20120423 - 20120622 mon-fri
      6 => [['20120424', '20120524', '20120605'], ['20120602', '20120506']],
      # 20120428 - 20120623 sat
      7 => [['20120505', '20120526'], ['20120506', '20120606']],
      # 20120326 - 20120416 mon
      8 => [['20120409'], ['20120410']],
      # 20120327 - 20120417 tue
      9 => [['20120410', '20120327'], ['20120328', '20120409']],
    }

    ServicePeriod.all.length.should be > 0

    ServicePeriod.all.each do |sp|
      if checks.key? sp.id
        ch = checks[sp.id]
        ch[0].each { |dts| sp.in_service?(Date.parse(dts)).should be_true, "#{dts} for #{sp} was not in_service" }
        ch[1].each { |dts| sp.in_service?(Date.parse(dts)).should be_false, "#{dts} for #{sp} was in_service" }
      end
    end
  end
end
