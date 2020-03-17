import hassapi as hass
import datetime
from datetime import timedelta
import math



class update_lights(hass.Hass):
    def initialize(self):
        now = datetime.datetime.now()
        #Import all user settings
        self.all_lights = self.args.get('entities', None)
        self.disable_entity = list(self.args.get('disable_entity', []))
        self.disable_condition = self.args.get('disable_condition', None)
        self.sleep_entity = list(self.args.get('sleep_entity', []))
        self.sleep_condition = self.args.get('sleep_condition', None)
        self.sleep_color = self.args.get('sleep_color', 'red')
        self.max_brightness_level = self.args.get('max_brightness_level', 255)
        self.min_brightness_level = self.args.get('min_brightness_level', 3)
        self.brightness_unit = self.args.get('brightness_unit', 'bit')
        self.brightness_threshold = self.args.get('brightness_threshold', 255)
        self.transition = self.args.get('transition', 5)
        self.start_time = self.args.get('start_time', 'sunset')
        self.end_time = self.args.get('end_time', 'sunrise')
        self.red_hour = self.args.get('red_hour', None)        
        self.start_index = self.args.get('start_index', self.start_time)
        self.end_index = self.args.get('end_index', self.end_time)
        self.color_temp_unit = self.args.get('color_temp_unit', 'kelvin')
        self.color_temp_max = self.args.get('color_temp_max', 4000)
        self.color_temp_min = self.args.get('color_temp_min', 2200)
        self.keep_lights_on = self.args.get('keep_lights_on', False)
        self.start_lights_on = self.args.get('start_lights_on', False)
        self.stop_lights_off = self.args.get('stop_lights_off', False)

        #Basic error checking
        if not isinstance(self.transition, int) or self.transition > 300:
            self.transition = 5

        if self.brightness_unit == 'percent':
            #Convert to bit
            self.brightness_threshold = int(self.brightness_threshold * 2.55)
            self.max_brightness_level = int(self.max_brightness_level * 2.55)
            self.min_brightness_level = int(self.min_brightness_level * 2.55)
        if not isinstance(self.brightness_threshold, int) or self.brightness_threshold > 255:
            self.brightness_threshold = 255
        if not isinstance(self.max_brightness_level, int) or self.max_brightness_level > 255:
            self.max_brightness_level = 255
        if not isinstance(self.min_brightness_level, int) or self.min_brightness_level > 255 or self.min_brightness_level > self.max_brightness_level:
            self.min_brightness_level = 3

        if isinstance(self.all_lights, str):
            self.all_lights = self.all_lights.split(',')

        if self.keep_lights_on or str(self.keep_lights_on).lower() == 'true':
            self.keep_lights_on = True
        else:
            self.keep_lights_on = False

        if self.start_lights_on or str(self.start_lights_on).lower() == 'true':
            self.start_lights_on = True
            self.run_daily(self.lights_on, self.parse_time(self.start_time))
        else:
            self.start_lights_on = False

        if self.stop_lights_off or str(self.stop_lights_off).lower() == 'true':
            self.stop_lights_off = True
            self.run_daily(self.lights_off, self.parse_time(self.end_time))
        else:
            self.stop_lights_off = False

        #Set callbacks for time interval, and subscribe to individual lights and disable entities
        interval = int(self.args.get('run_every', 60))
        target = now + timedelta(seconds=interval)
        if self.all_lights is not None:
            if self.disable_entity is not None:
                for entity in self.disable_entity:
                    if len(entity.split(',')) > 1:
                        entity = entity.split(',')[0]
                    self.listen_state(self.state_change, entity)
            if self.sleep_entity is not None:
                for entity in self.sleep_entity:
                    if len(entity.split(',')) > 1:
                        entity = entity.split(',')[0]
                    self.listen_state(self.state_change, entity)
            for light in self.all_lights:
                self.listen_state(self.state_change, light)
            self.run_every(self.time_change, target, interval)
        else:
            self.log('No lights defined', log='error_log')

    def time_change(self, kwargs):
        threshold = self.brightness_threshold
        transition = self.transition
        entities = self.all_lights
        self.adjust_light(entities, threshold, transition)

    def state_change(self, entity, attribute, old, new, kwargs):
        threshold = 255
        transition = 0
        if entity in self.all_lights and new == "on":
            self.adjust_light(entity, threshold, transition)
            return
        if self.disable_entity is not None:
            for check_entity in self.disable_entity:
                if entity == check_entity.split(',')[0] and not self.condition_query(self.disable_entity, self.disable_condition):
                    self.adjust_light(self.all_lights, threshold, transition)
                    return
        if self.sleep_entity is not None:
            for check_entity in self.sleep_entity:
                if entity == check_entity.split(',')[0]:
                    self.adjust_light(self.all_lights, threshold, transition)
                    return

    def lights_on(self, kwargs):
        #Turn on all lights
        for entity in self.all_lights:
            self.turn_on(entity)

    def lights_off(self, kwargs):
        #Turn off all lights
        for entity in self.all_lights:
            self.turn_off(entity)

    def pct(self):
        ##########################
        # Calculate night percent
        ##########################
        dt = datetime.datetime.now()
        now_time = dt.timestamp()

        start_ts = datetime.datetime.combine(self.date(), self.parse_time(self.start_time))
        end_ts = datetime.datetime.combine(self.date(), self.parse_time(self.end_time))
        midnight = '0:00:00'

        if self.now_is_between(self.start_time, self.end_time):
            #We are in between the start and end times
            if self.now_is_between(midnight, self.end_time) and int(start_ts.timestamp()) > int(end_ts.timestamp()):
                #We are past midnight and the start time was the day before
                start_ts = start_ts + timedelta(days=-1)
            elif int(start_ts.timestamp()) > int(end_ts.timestamp()):
                #We are before midnight and the end time is after midnight
                end_ts = end_ts + timedelta(days=1)

        start_i_ts = datetime.datetime.combine(start_ts.date(), self.parse_time(self.start_index))
        end_i_ts = datetime.datetime.combine(end_ts.date(), self.parse_time(self.end_index))

        start_ts = int(start_ts.timestamp())
        end_ts = int(end_ts.timestamp())
        start_i_ts = int(start_i_ts.timestamp())
        end_i_ts = int(end_i_ts.timestamp())
        #Calculate the midpoint between start and end time incorpertaing the indexed times
        midpoint_start = (start_i_ts + end_ts) / 2
        midpoint_end = (start_ts + end_i_ts) / 2
        if now_time < midpoint_start:
            midpoint = midpoint_start
        else:
            midpoint = midpoint_end
        
        if now_time < start_ts and now_time > end_ts:
            #We are outside of the start and end time so 0 dimming
            pct = 0
        else:
            if now_time < midpoint:
                #We are after start time but before midpoint (ramp down)
                pct = float((now_time - start_ts) / (midpoint - start_ts))
            else:
                #We are after midpoint but before end time (ramp up)
                pct = 1 - float((now_time - midpoint) / (end_ts - midpoint))
        return pct

    def color(self, pct):
        color_max = self.color_temp_max
        color_min = self.color_temp_min
        if self.color_temp_unit != 'kelvin' and self.color_temp_unit != 'mired':
            #Catch the case where the user entered bad information or had a typo
            color_max = 4000
            color_min = 2200
            self.color_temp_unit = 'kelvin'
        elif self.color_temp_unit == 'mired':
            #Switch to kelvin for the calculation
            color_max = self.color_temperature_mired_to_kelvin(color_max)
            color_min = self.color_temperature_mired_to_kelvin(color_min)

        sleep_state = self.condition_query(self.sleep_entity, self.sleep_condition)

        if sleep_state == False:
            #Calculate desired color temp
            desired_temp_kelvin = round(int(color_max) - (abs(int(color_max) - int(color_min))* float(pct)))
        else:
            desired_temp_kelvin = color_min
        desired_temp_mired = self.color_temperature_kelvin_to_mired(desired_temp_kelvin)
        return int(desired_temp_kelvin), int(desired_temp_mired)

    def rgb_color(self, desired_temp):

        ###########################
        #Color temp to rgb copied from HASS color utils
        ###########################

        desired_temp=desired_temp/100

        if desired_temp <= 66:
            tmp_red = 255 - (desired_temp / 2)
            tmp_green = desired_temp
            tmp_green = 99.4708025861 * (0.0336982 * tmp_green + 1.96562) - 161.1195681661 + 75
            if desired_temp <= 19:
                tmp_blue = 0
            else:
                tmp_blue = desired_temp - 10
                tmp_blue = 138.5177312231 * (0.0264957 * tmp_blue  + 2.44098) - 305.0447927307 + 75
        else:
            tmp_red = desired_temp - 0
            tmp_red = 329.698727446 * tmp_red ** -0.1332047592
            
            tmp_green = desired_temp - 60
            tmp_green = 288.1221695283 * tmp_green ** -0.0755148492 

            tmp_blue = 255
            
        tmp_red = round(tmp_red)
        tmp_green = round(tmp_green)
        tmp_blue = round(tmp_blue)

        if tmp_red < 0:
            tmp_red = 0
        elif tmp_red > 255:
            tmp_red = 255
            
        if tmp_green < 0:
            tmp_green = 0
        elif tmp_green > 255:
            tmp_green = 255
            
        if tmp_blue < 0:
            tmp_blue = 0
        elif tmp_blue > 255:
            tmp_blue = 255
        return tmp_red, tmp_green, tmp_blue
        
    def brightness(self, pct):
        max_brightness_level = self.max_brightness_level
        min_brightness_level = self.min_brightness_level
        brightness_unit = self.brightness_unit

        #Calculate brightness level in the defined range
        brightness_level = int(max_brightness_level) - round(int(max_brightness_level - min_brightness_level) * pct)

        sleep_state = self.condition_query(self.sleep_entity, self.sleep_condition)

        if int(brightness_level) > int(max_brightness_level) and sleep_state != True:
            #If we are above 255 correct for that
            brightness_level = int(max_brightness_level)
        elif int(brightness_level) < int(min_brightness_level) or sleep_state == True:
            #If we are below min or are in sleep state
            return int(min_brightness_level)
        return brightness_level

    def red_hour_query (self):
        if self.red_hour is not None:
            if self.now_is_between(self.red_hour, self.end_time):
                return True
            else:
                return False
        else:
            return False

    def condition_query (self, entities, condition = None):
        value = False
        condition_states = ['on', 'Home', 'home', 'True', 'true']
        if condition is not None:
            condition_states.append(condition.split(','))
        if entities is not None:
            for entity in entities:
                if len(entity.split(',')) > 1:
                    if entity.split(',')[1] == self.get_state(entity.split(',')[0]):
                        value = True
                elif self.get_state(entity) == True or self.get_state(entity) in condition_states:
                    value = True
        return value

    def color_temperature_mired_to_kelvin(self, mired_temperature: float) -> float:
        """Convert absolute mired shift to degrees kelvin."""
        return math.floor(1000000 / mired_temperature)

    def color_temperature_kelvin_to_mired(self, kelvin_temperature: float) -> float:
        """Convert degrees kelvin to mired shift."""
        return math.floor(1000000 / kelvin_temperature)

    def adjust_light(self, entities, threshold, transition):

        override = self.condition_query(self.disable_entity, self.disable_condition)

        if override:
            return None

        if 'companion_script' in self.args:
            self.turn_on(entity_id=self.args['companion_script'])

        dt = datetime.datetime.now()

        pct = self.pct()

        if 'sensor_log' in self.args:
            self.set_state(self.args['sensor_log'], state=(pct*100),  attributes = {"unit_of_measurement":"%", "note":"Percentage of dimming, inverted to brightness percent"})

        brightness_level = self.brightness(pct)
        desired_temp_kelvin, desired_temp_mired = self.color(pct)
        sleep_state = self.condition_query(self.sleep_entity, self.sleep_condition)
        red_hour = self.red_hour_query()

        ##########################
        # Change light temp and brightness if conditions are met
        ##########################

        if isinstance(entities, str):
            entities = entities.split(',')
        color_temp_list = []
        kelvin_list = []
        rgb_list = []
        brightness_only_list = []

        rgb_service_data = {"brightness": brightness_level, "transition": transition}
        color_temp_service_data = {"brightness": brightness_level, "transition": transition}
        kelvin_service_data = {"brightness": brightness_level, "transition": transition}
        brightness_only_service_data = {"brightness": brightness_level, "transition": transition}

        for entity_id in entities:
            cur_state = self.get_state(entity_id)
            if (cur_state == 'on' or self.keep_lights_on):
                brightness = self.get_state(entity_id, attribute="brightness")
                if (brightness is not None and (abs(int(brightness) - int(brightness_level)) < int(threshold)) and int(brightness) != int(brightness_level)) or self.keep_lights_on or (red_hour and sleep_state):
                    color_temp = self.get_state(entity_id, attribute='color_temp')
                    kelvin = self.get_state(entity_id, attribute='kelvin')
                    rgb_color = self.get_state(entity_id, attribute='rgb_color')
                    if (rgb_color is not None and color_temp is None and kelvin is None) or (red_hour == True and sleep_state == True and rgb_color is not None):
                        rgb_list.append(entity_id)
                    elif color_temp is not None:
                        color_temp_list.append(entity_id)
                    elif kelvin is not None:
                        kelvin_list.append(entity_id)
                    else:
                        brightness_only_list.append(entity_id)

        if rgb_list:
            if red_hour and sleep_state:
                tmp_red = 255
                tmp_green = 0
                tmp_blue = 0
                rgb_service_data['brightness'] = int((self.max_brightness_level + self.min_brightness_level) / 2)
                rgb_service_data['color_name'] = self.sleep_color
            else:
                tmp_red, tmp_green, tmp_blue = self.rgb_color(desired_temp_kelvin)
                rgb_service_data['rgb_color'] = [int(tmp_red), int(tmp_green), int(tmp_blue)]
            rgb_service_data['entity_id'] = rgb_list
            self.call_service("light/turn_on", **rgb_service_data)

        if color_temp_list:
            color_temp_service_data['entity_id'] = color_temp_list
            color_temp_service_data['color_temp'] = desired_temp_mired
            self.call_service("light/turn_on", **color_temp_service_data)

        if kelvin_list:
            kelvin_service_data['entity_id'] = kelvin_list
            kelvin_service_data['kelvin'] = desired_temp_kelvin
            self.call_service("light/turn_on", **kelvin_service_data)

        if brightness_only_list:
            brightness_only_service_data['entity_id'] = brightness_only_list
            self.call_service("light/turn_on", **brightness_only_service_data)
