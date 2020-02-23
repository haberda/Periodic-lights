# update_lights
## This code acts on a list of lights to primarialy do two things: 

1) Gradually change the brightness level and the color temperature of the lights from the start to end time ONLY if the lights are currently on
2) When a light in the list is turned on and its brightness is not equal to the current level it immediatly changes the settings to match other lights

What makes this code different than others (namely custom component Circadian Lighting or Flux component) is the implementation of change thresholds; 
so if someone manually adjusts a light outside of the threshold range the code will skip that light.
The brightness/color temp is calculated by determining how far from the middle point of the start and end time the current time is
in other words at start time and end time there is 100% brightness, at the exact middle point there is 0% brightness (or whatever the configured max and min are)
All lights can be mixed e.g. you can have a list with RGB, color temp, and brightness only lights together
There are numerous options that can be configured to adjust the gradient of the change and constrain whether or not the code is active

Options:
---
entities (required list of lights)

run_every (time interval in seconds to run the code, optional default:60)

start_time (time in format 'HH:MM:SS' to start; also can be 'sunset - HH:MM:SS', optional default: sunset)

end_time (time in format 'HH:MM:SS' to start; also can be 'sunrise - HH:MM:SS', optional default: sunrise)

start_index (with this option you can push the middle point left or right and increase or decrease the brightness change gradient and point of minimum brightness/temp, takes time the same was as start/end times, optional default: None)

end_index (same as start index but changes the end time rather than start both can be configured to have 2 minimum brightness points)

brightness_threshold (residual threshold between calculated brightness and current brightness if residual > this no change, percent or bit, optional default 255)

brightness_unit (percent or bit, optional default: bit)

max_brightness_level (max brightness level, optional default: 255 or 100 depending on bit or percent unit)

min_brightness_level (max brightness level, optional default: 3 or 1 depending on bit or percent unit)

color_temp_unit (kelvin or mired color temp unit, optional default: kelvin)

color_temp_max (maximum color temp, optional default: 4000 kelvin)

color_temp_min (min color temp, optional default: 2200 kelvin)

disable_entity (list of entities that when active disable the functionality of this code, optional)

disable_condition (override default condition check for disable_entity, optional default:on, true, or Home)

sleep_entity (list of entities that track whether a 'sleep mode' has been enabled this immediatly brings lights to the lowest brightness and color temp defined, optional)

sleep_condition (override default condition check for sleep_entity, optional default:on, true, or Home)

red_hour (time in format 'HH:MM:SS' during the start and stop times that the RGB lights turn red if sleep conditions are met, optional)

transition (light transition time in seconds, optional default: 5)

companion_script (script to execute before changing lights, useful to force Zwave lights to update state, optional)

sensor_log (creates a sensor to track the dimming percentage, mostly for diagnostic purposes, format: sensor.my_sensor, optional)

keep_lights_on (forces the light to turn on, in other words ignores that it is off, Boolean: True or False, default: False)

start_lights_on (turn on the lights at the start time)

stop_lights_off (turn off the lights at the stop time)

AppDaemon constraints can be used as well, see AppDaemon API Docs https://appdaemon.readthedocs.io/en/latest/APPGUIDE.htmlcallback-constraints

## Example apps.yaml:

```
main_update_lights:
  module: update_lights
  class: update_lights
  run_every: 180
  entities:
    - light.back_hallway
    - light.coffee_bar
    - light.dans_bedside
    - light.erins_bedside
    - light.group_family_room
    - light.guest_room
    - light.kitchen2
    - light.kitchen_spotlight
    - light.kitchen_spotlight_left
    - light.kitchen_spotlight_right
    - light.living_room_dimmer
    - light.living_room_lamp
    - light.living_room_lamp_2
    - light.main_cabinets
    - light.mb_fan
  brightness_threshold: 50
  color_temp_max: 250
  color_temp_min: 500
  color_temp_unit: 'mired'
  max_brightness_level: 100
  min_brightness_level: 1
  brightness_unit: 'percent'
  sleep_entity: 
    - input_boolean.bedtime
    - switch.dan_bedtime
    - switch.erin_bedtime
  red_hour: '21:00:00'
  start_time: sunset - 3:00:00
  end_time: sunrise + 2:00:00
  start_index: sunset - 4:00:00
  end_index: sunrise + 6:00:00
  transition: 5
  keep_lights_on: False
  stop_lights_off: True
  disable_entity: 
    - input_boolean.party_mode
    - input_boolean.hold_lights
    - input_boolean.disco
  sensor_log: sensor.main_lights
  
exterior_update_lights:
  module: test
  class: update_lights
  run_every: 180
  entities:
    - light.group_backyard
    - light.group_exterior_garage
  min_brightness_level: 102
  start_time: sunset - 0:20:00
  end_time: sunrise + 0:00:00
  transition: 0
  start_lights_on: True
  stop_lights_off: True
  constrain_start_time: sunset - 0:30:00
  constrain_end_time: sunrise + 0:10:00
```
