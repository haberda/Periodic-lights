# update_lights
## This code acts on a list of lights to primarily do two things: 

1) Gradually change the brightness level and the color temperature of the lights from the start to end time ONLY if the lights are currently on
2) When a light in the list is turned on and its brightness is not equal to the current level it immediately changes the settings to match other lights

What makes this code different than others (namely custom component Circadian Lighting or Flux component) is the implementation of change thresholds; 
so if someone manually adjusts a light outside of the threshold range the code will skip that light.
The brightness/color temp is calculated by determining how far from the middle point of the start and end time the current time is
in other words at start time and end time there is 100% brightness, at the exact middle point there is 0% brightness (or whatever the configured max and min are)
All lights can be mixed e.g. you can have a list with RGB, color temp, and brightness only lights together
There are numerous options that can be configured to adjust the gradient of the change and constrain whether or not the code is active

Options:
---

Key | Required | Description | Default | Unit
------------ | ------------- | ------------- | ------------- | -------------
entities | True | List of lights | None | List
run_every | False | Time interval in seconds to run the code | 60 | Seconds
start_time | False | Time in format 'HH:MM:SS' to start; also can be 'sunset - HH:MM:SS' | sunset | Time
end_time | False | Time in format 'HH:MM:SS' to start; also can be 'sunrise - HH:MM:SS' | sunrise | Time
start_index  | False | With this option you can push the middle point left or right and increase or decrease the brightness change gradient and point of minimum brightness/temp, takes time the same was as start/end times | None | Time
end_index | False | Same as start index but changes the end time rather than start both can be configured to have 2 minimum brightness points | None | Time
brightness_threshold | False | Residual threshold between calculated brightness and current brightness if residual > this no change | 255 or 100 | Bit or percent
brightness_unit | False | percent or bit | bit | None
max_brightness_level | False | Max brightness level | 255 or 100 | Bit or percent
min_brightness_level | False | Max brightness level | 3 or 1 | Bit or percent
color_temp_unit | False | Kelvin or mired color temp unit | kelvin | 
color_temp_max | False | Maximum color temp | 4000 | kelvin
color_temp_min | False | Min color temp | 2200 | kelvin
disable_entity | False | List of entities that when active disable the functionality of this code. Can take a comma separated condition rather than disable condition key below (e.g. input_boolean.party_mode,on) | None | List
disable_condition | False | Override default condition check for disable_entity | on, True, or Home | Boolean or string in list form
sleep_entity | False | List of entities that track whether a 'sleep mode' has been enabled this immediatly brings lights to the lowest brightness and color temp defined. Can take a comma separated condition rather than disable condition key below (e.g. input_boolean.sleep_mode,on) | None | List
sleep_condition | False | Override default condition check for sleep_entity | on, True, or Home | Boolean or string in list form
red_hour | False | Time in format 'HH:MM:SS' during the start and stop times that the RGB lights turn red if sleep conditions are met | None | Time
transition | False | Light transition time in seconds | 5 | Seconds
companion_script | False | Script to execute before changing lights, useful to force Zwave lights to update state | None | 
sensor_log | False | Creates a sensor to track the dimming percentage, mostly for diagnostic purposes, format: sensor.my_sensor | None | 
keep_lights_on | False | Forces the light to turn on, in other words ignores that it is off | False | Boolean
start_lights_on | False | Turn on the lights at the start time | False | Boolean
stop_lights_off | False | Turn off the lights at the stop time | False | Boolean

AppDaemon constraints can be used as well, see AppDaemon API Docs https://appdaemon.readthedocs.io/en/latest/APPGUIDE.html#callback-constraints

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
  brightness_threshold: 25
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
  start_index: '17:00:00'
  end_index: '08:00:00'
  transition: 5
  keep_lights_on: False
  stop_lights_off: True
  disable_entity: 
    - input_boolean.party_mode,on
    - input_boolean.hold_lights,on
    - input_boolean.disco,on
    - sensor.arbitrary_sensor,arbitrary_condition
  sensor_log: sensor.main_lights
  
exterior_update_lights:
  module: update_lights
  class: update_lights
  run_every: 180
  entities:
    - light.group_backyard
    - light.group_exterior_garage
  min_brightness_level: 102
  start_time: sunset - 0:20:00
  end_time: sunrise
  transition: 0
  start_lights_on: True
  stop_lights_off: True
```
