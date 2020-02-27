import hassapi as hass
import datetime
from datetime import timedelta
import math

class update_lights(hass.Hass):
    def initialize(self):
        now = datetime.datetime.now()

        self.all_lights = self.args.get('entities', None)
        self.disable_entity = self.args.get('disable_entity', None)
        self.disable_condition = self.args.get('disable_condition', None)
        self.sleep_entity = self.args.get('sleep_entity', None)
        self.sleep_condition = self.args.get('sleep_condition', None)
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

        if not isinstance(self.transition, int) or self.transition > 300:
            self.transition = 5

        if not isinstance(self.brightness_threshold, int) or self.brightness_threshold > 255:
            self.brightness_threshold = 255

        if isinstance(self.all_lights, str):
            self.all_lights = self.all_lights.split(',')

        if isinstance(self.disable_entity, str):
            self.disable_entity = self.disable_entity.split(',')

        if isinstance(self.sleep_entity, str):
            self.sleep_entity = self.sleep_entity.split(',')

        if self.keep_lights_on or str(self.keep_lights_on).lower() == 'true':
            self.keep_lights_on = True
        else:
            self.keep_lights_on = False

        if self.start_lights_on or str(self.start_lights_on).lower() == 'true':
            self.start_lights_on = True
            self.run_daily(self.lights_on, self.parse_time(self.start_time))
            self.log(self.parse_time(self.start_time))
        else:
            self.start_lights_on = False

        if self.stop_lights_off or str(self.stop_lights_off).lower() == 'true':
            self.stop_lights_off = True
            self.run_daily(self.lights_off, self.parse_time(self.end_time))
            self.log(self.parse_time(self.end_time))
        else:
            self.stop_lights_off = False

        interval = int(self.args.get('run_every', 60))
        target = now + timedelta(seconds=interval)
        if self.all_lights is not None:
            if self.disable_entity is not None:
                for entity in self.disable_entity:
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
        if self.disable_entity is not None:
            for check_entity in self.disable_entity:
                if entity == check_entity and (((old == 'on' or old == True or old == 'Home' or old == 'True')  and self.disable_condition == None) or old == self.disable_condition):
                    self.adjust_light(self.all_lights, threshold, transition)

    def lights_on(self, kwargs):
        self.log('Lights on')
        for entity in self.all_lights:
            self.turn_on(entity)

    def lights_off(self, kwargs):
        self.log('Lights off')
        for entity in self.all_lights:
            self.turn_off(entity)

    def pct(self):
        ##########################
        # Night percent
        ##########################
        dt = datetime.datetime.now()
        now_time = dt.timestamp()

        start_ts = datetime.datetime.combine(self.date(), self.parse_time(self.start_time))
        end_ts = datetime.datetime.combine(self.date(), self.parse_time(self.end_time))
        midnight = '0:00:00'

        if self.now_is_between(self.start_time, self.end_time):
            if self.now_is_between(midnight, self.end_time) and int(start_ts.timestamp()) > int(end_ts.timestamp()):
                start_ts = start_ts + timedelta(days=-1)
            elif int(start_ts.timestamp()) > int(end_ts.timestamp()):
                end_ts = end_ts + timedelta(days=1)

        start_i_ts = datetime.datetime.combine(start_ts.date(), self.parse_time(self.start_index))
        end_i_ts = datetime.datetime.combine(end_ts.date(), self.parse_time(self.end_index))

        start_ts = int(start_ts.timestamp())
        end_ts = int(end_ts.timestamp())
        start_i_ts = int(start_i_ts.timestamp())
        end_i_ts = int(end_i_ts.timestamp())
        
        midpoint_start = (start_i_ts + end_ts) / 2
        midpoint_end = (start_ts + end_i_ts) / 2
        if now_time < midpoint_start:
            midpoint = midpoint_start
        else:
            midpoint = midpoint_end
        
        if now_time < start_ts and now_time > end_ts:
            pct = 0
        else:
            if now_time < midpoint:
                pct = float((now_time - start_ts) / (midpoint - start_ts))
            else:
                pct = 1 - float((now_time - midpoint) / (end_ts - midpoint))
        return pct

    def color(self, pct):

        color_max = self.color_temp_max
        color_min = self.color_temp_min
        if self.color_temp_unit != 'kelvin' and self.color_temp_unit != 'mired':
            color_max = 4000
            color_min = 2200
            self.color_temp_unit = 'kelvin'
        elif self.color_temp_unit == 'mired':
            color_max = self.color_temperature_mired_to_kelvin(color_max)
            color_min = self.color_temperature_mired_to_kelvin(color_min)

        sleep_state = self.sleep_query()

        if sleep_state == False:
            desired_temp_kelvin = round(int(color_max) - (abs(int(color_max) - int(color_min))* float(pct)))
        else:
            desired_temp_kelvin = color_min
        desired_temp_mired = self.color_temperature_kelvin_to_mired(desired_temp_kelvin)
        return int(desired_temp_kelvin), int(desired_temp_mired)

    def rgb_color(self, desired_temp):

        ###########################
        #Color temp to rgb
        ###########################

        desired_temp=desired_temp/100

        if desired_temp <= 66:
            tmp_red = 255 - (desired_temp / 2)
            tmp_green = desired_temp
            tmp_green = 99.4708025861 * (0.0336982 * tmp_green + 1.96562) - 161.1195681661 + 50
            if desired_temp <= 19:
                tmp_blue = 0
            else:
                tmp_blue = desired_temp - 10
                tmp_blue = 138.5177312231 * (0.0264957 * tmp_blue  + 2.44098) - 305.0447927307 + 50
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

        if brightness_unit == 'percent':
            max_brightness_level = int(max_brightness_level) * 2.55
            min_brightness_level = int(min_brightness_level) * 2.55

        brightness_level = int(max_brightness_level) - round(int(max_brightness_level - min_brightness_level) * pct)

        sleep_state = self.sleep_query()

        if int(brightness_level) > int(max_brightness_level) and sleep_state != True:
            brightness_level = int(max_brightness_level)
        elif int(brightness_level) < int(min_brightness_level) or sleep_state == True:
            return int(min_brightness_level)
        return brightness_level

    def sleep_query (self):
        sleep_state = False
        if self.sleep_entity is not None:
            for sleep in self.sleep_entity:
                if ((self.get_state(sleep) == 'on' or self.get_state(sleep) == True or self.get_state(sleep) == 'True' or self.get_state(sleep) == 'Home') and self.sleep_condition == None) or self.get_state(sleep) == self.sleep_condition:
                    sleep_state = True
        return sleep_state

    def red_hour_query (self):
        if self.red_hour is not None:
            if self.now_is_between(self.red_hour, self.end_time):
                return True
            else:
                return False
        else:
            return False

    def disabled_query (self):
        query = False
        if self.disable_entity is not None:
            for entity in self.disable_entity:
                disable_state = self.get_state(entity)
                if ((disable_state == 'on' or disable_state == True or disable_state == 'True' or disable_state == 'Home') and self.disable_condition == None) or disable_state == self.disable_condition:
                    query = True
            return query
        else:
            return query

    def color_temperature_mired_to_kelvin(self, mired_temperature: float) -> float:
        """Convert absolute mired shift to degrees kelvin."""
        return math.floor(1000000 / mired_temperature)

    def color_temperature_kelvin_to_mired(self, kelvin_temperature: float) -> float:
        """Convert degrees kelvin to mired shift."""
        return math.floor(1000000 / kelvin_temperature)

    def adjust_light(self, entities, threshold, transition):

        override = self.disabled_query()

        if override:
            return None

        if 'companion_script' in self.args:
            self.turn_on(entity_id=self.args['companion_script'])

        dt = datetime.datetime.now()

        pct = self.pct()

        if 'sensor_log' in self.args:
            self.set_state(self.args['sensor_log'], state=pct,  attributes = {"unit_of_measurement":"%"})

        brightness_level = self.brightness(pct)
        desired_temp_kelvin, desired_temp_mired = self.color(pct)
        sleep_state = self.sleep_query()
        red_hour = self.red_hour_query()

        ##########################
        # Change light temp and brightness if conditions are met
        ##########################

        if isinstance(entities, str):
            entities = entities.split(',')

        for entity_id in entities:
            if self.entity_exists(entity_id):
                cur_state = self.get_state(entity_id)
                brightness = self.get_state(entity_id, attribute="brightness")
                if (brightness is not None and (abs(int(brightness) - int(brightness_level)) < float(threshold)) and int(brightness) != int(brightness_level)) or self.keep_lights_on or (red_hour and sleep_state):
                    if (cur_state == 'on' or self.keep_lights_on):
                        color_temp = self.get_state(entity_id, attribute='color_temp')
                        kelvin = self.get_state(entity_id, attribute='kelvin')
                        rgb_color = self.get_state(entity_id, attribute='rgb_color')
                        if color_temp is not None or rgb_color is not None or kelvin is not None:
                            if rgb_color is not None and (color_temp is None and kelvin is None) and sleep_state != True:
                                tmp_red, tmp_green, tmp_blue = self.rgb_color(desired_temp_kelvin)
                                self.turn_on(entity_id = entity_id, brightness = brightness_level, transition = transition , rgb_color = [int(tmp_red), int(tmp_green), int(tmp_blue)])
                            elif red_hour == True and sleep_state == True and rgb_color is not None:
                                self.turn_on(entity_id = entity_id, brightness = int(255), transition = transition , color_name = "red")
                            elif (color_temp is not None and self.color_temp_unit == 'mired') or (self.color_temp_unit == 'kelvin' and kelvin is None):
                                self.turn_on(entity_id = entity_id, brightness = brightness_level, transition = transition , color_temp = desired_temp_mired)
                            elif (color_temp is None and self.color_temp_unit == 'mired') or (self.color_temp_unit == 'kelvin' and kelvin is not None):
                                self.turn_on(entity_id = entity_id, brightness = brightness_level, transition = transition , kelvin = desired_temp_kelvin)
                        else:
                            self.turn_on(entity_id = entity_id, brightness = brightness_level, transition = transition)
            else:
                self.log('No state for {}.'.format(entity_id))
