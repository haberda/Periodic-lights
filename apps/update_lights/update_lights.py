import hassapi as hass
import datetime
from datetime import timedelta
import math

class update_lights_beta(hass.Hass):
    def initialize(self):
        now = datetime.datetime.now()
        #Import all user settings
        self.all_lights = self.args.get('entities', [])
        self.disable_entity = self.args.get('disable_entity', [])
        self.disable_condition = self.args.get('disable_condition', [])
        self.sleep_entity = self.args.get('sleep_entity', [])
        self.sleep_condition = self.args.get('sleep_condition', [])
        self.sleep_color = str(self.args.get('sleep_color', 'red'))
        self.max_brightness_level = int(self.args.get('max_brightness_level', 255))
        self.min_brightness_level = int(self.args.get('min_brightness_level', 3))
        self.brightness_unit = str(self.args.get('brightness_unit', 'bit'))
        self.brightness_threshold = int(self.args.get('brightness_threshold', 255))
        self.transition = int(self.args.get('transition', 5))
        self.start_time = str(self.args.get('start_time', 'sunset'))
        self.end_time = str(self.args.get('end_time', 'sunrise'))
        self.perfer_rgb = bool(self.args.get('perfer_rgb', False))
        self.start_index = str(self.args.get('start_index', self.start_time))
        self.end_index = str(self.args.get('end_index', self.end_time))
        self.color_temp_unit = str(self.args.get('color_temp_unit', 'kelvin'))
        self.color_temp_max = int(self.args.get('color_temp_max', 4000))
        self.color_temp_min = int(self.args.get('color_temp_min', 2200))
        self.sleep_color_temp = int(self.args.get('sleep_color_temp', self.color_temp_min))
        self.watch_light_state = self.args.get('watch_light_state', True)
        self.keep_lights_on = self.args.get('keep_lights_on', False)
        self.start_lights_on = self.args.get('start_lights_on', False)
        self.stop_lights_off = self.args.get('stop_lights_off', False)
        self.sensor_only = self.args.get('sensor_only', False)
        self.event = self.args.get('event_subscription', None)

        interval = int(self.args.get('run_every', 180))
        target = now + timedelta(seconds=interval)

        if self.sensor_only and self.sensor_only != 'false':
            #Sensor only is specified
            self.run_every(self.time_change, target, interval)
            return
        else:
            self.sensor_only = False

        if isinstance(self.all_lights, str):
            self.all_lights = self.all_lights.split(',')
        if isinstance(self.disable_entity, str):
            self.disable_entity = self.disable_entity.split('*')
        if isinstance(self.disable_condition, str):
            self.disable_condition = self.disable_condition.split(',')
        if isinstance(self.sleep_entity, str):
            self.sleep_entity = self.sleep_entity.split('*')
        if isinstance(self.sleep_condition, str):
            self.sleep_condition = self.sleep_condition.split(',')

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

        if str(self.keep_lights_on).lower() == 'false':
            self.keep_lights_on = False
        else:
            self.keep_lights_on = True

        if str(self.start_lights_on).lower() == 'false':
            self.start_lights_on = False
        else:
            self.start_lights_on = True
            self.run_daily(self.lights_on, self.parse_time(self.start_time))

        if str(self.stop_lights_off).lower() == 'false':
            self.stop_lights_off = False
        else:
            self.stop_lights_off = True
            self.run_daily(self.lights_off, self.parse_time(self.end_time))


        #Set callbacks for time interval, and subscribe to individual lights and disable/sleep entities

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
            if self.watch_light_state:
                for light in self.all_lights:
                    self.listen_state(self.state_change, light, oneshot = True)
            if interval > 0:
                self.run_every(self.time_change, target, interval)
            if self.event is not None:
                self.listen_event(self.event_subscription, self.event)
        else:
            self.log('No lights defined', log='error_log')

    def time_change(self, kwargs):
        threshold = self.brightness_threshold
        transition = self.transition
        entities = self.all_lights
        self.adjust_light(entities, threshold, transition)

    def event_subscription(self, event, data, kwargs):
        threshold = 255
        if 'threshold' in data:
            threshold = data['threshold']
        transition = 0
        if 'transition' in data:
            transition = data['transition']
        entities = self.all_lights
        self.adjust_light(entities, threshold, transition)

    def state_change(self, entity, attribute, old, new, kwargs):
        threshold = 255
        transition = 0
        if entity in self.all_lights:
            if new == "on":
                self.adjust_light(entity, threshold, transition)
            self.run_in(self.resubscribe, 2, entity = entity)
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

    def resubscribe (self, kwargs):
        self.listen_state(self.state_change, kwargs['entity'], oneshot = True)

    def lights_on(self, kwargs):
        #Turn on all lights
        check = self.condition_query(self.disable_entity, self.disable_condition)
        if not check:
            for entity in self.all_lights:
                self.turn_on(entity)

    def lights_off(self, kwargs):
        #Turn off all lights
        check = self.condition_query(self.disable_entity, self.disable_condition)
        if not check:
            for entity in self.all_lights:
                self.turn_off(entity)

    def pct(self):
        """Calculate percentage through day"""
        dt = datetime.datetime.now()
        now_time = dt.timestamp()

        start = datetime.datetime.combine(self.date(), self.parse_time(self.start_time))
        end = datetime.datetime.combine(self.date(), self.parse_time(self.end_time))
        midnight = '0:00:00'
        if end > start and (self.now_is_between(self.end_time, self.start_time) or self.now_is_between(midnight, self.end_time)):
            self.log('Start and end occur in the same day. No time delta.')
        elif self.now_is_between(midnight, self.end_time) and not self.now_is_between(self.start_time, midnight):
            #We are past midnight and the start time was the day before
            self.log('Time delta start -1 day')
            start = start + timedelta(days=-1)
        elif self.now_is_between(self.end_time, midnight) and start > end:
            #We are before midnight and the end time is after midnight
            self.log('Time delta end +1 day')
            end = end + timedelta(days=1)
        #Get index times
        start_i = datetime.datetime.combine(start.date(), self.parse_time(self.start_index))
        end_i = datetime.datetime.combine(end.date(), self.parse_time(self.end_index))
        if start_i > end_i:
            #End is before midnight but end index is after
            end_i = end_i + timedelta(days=1)
        #Figure out midpoint
        half_seconds = (end - start).total_seconds() / 2
        half = start + timedelta(seconds=half_seconds)
        #Figure out start index midpoint
        half_seconds = (end - start_i).total_seconds() / 2
        midpoint_start = start_i + timedelta(seconds=half_seconds)
        #Figure out end index midpoint
        half_seconds = (end_i - start).total_seconds() / 2
        midpoint_end = start + timedelta(seconds=half_seconds)
        #Calculate the midpoint between start and end time incorpertaing the indexed times
        if (dt > midpoint_start and dt < midpoint_end) or (dt < midpoint_start and dt > midpoint_end):
            self.log('In the middle of the midpoints')
            pct = 0
        else:
            if dt < midpoint_start:
                # midpoint = midpoint_start.timestamp()
                midpoint = midpoint_end.timestamp()
            else:
                midpoint = midpoint_start.timestamp()
                # midpoint = midpoint_end.timestamp()
            pct = abs(float(math.sin(math.pi*((now_time - midpoint) / (86400)))))
        return pct, half, midpoint_start, midpoint_end

    def color(self, pct):
        color_max = self.color_temp_max
        color_min = self.color_temp_min
        color_sleep = self.sleep_color_temp
        if self.color_temp_unit != 'kelvin' and self.color_temp_unit != 'mired':
            #Catch the case where the user entered bad information or had a typo
            color_max = 4000
            self.color_temp_max = 4000
            color_min = 2200
            self.color_temp_min = 2200
            color_sleep = color_min
            self.sleep_color_temp = color_min
            self.color_temp_unit = 'kelvin'
        elif self.color_temp_unit == 'mired':
            #Switch to kelvin for the calculation
            color_max = self.color_temperature_mired_to_kelvin(color_max)
            color_min = self.color_temperature_mired_to_kelvin(color_min)
            color_sleep = self.color_temperature_mired_to_kelvin(color_sleep)
        sleep_state = self.condition_query(self.sleep_entity, self.sleep_condition)
        if sleep_state == False:
            #Calculate desired color temp
            desired_temp_kelvin = round(int(color_min) + (abs(int(color_max) - int(color_min))* float(pct)))
        else:
            desired_temp_kelvin = color_sleep
        desired_temp_mired = self.color_temperature_kelvin_to_mired(desired_temp_kelvin)
        return int(desired_temp_kelvin), int(desired_temp_mired)

    def rgb_color(self, desired_temp):
        """Color temp to rgb copied from HASS color util"""
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
        brightness_level = int(min_brightness_level) + round(int(max_brightness_level - min_brightness_level) * pct)

        sleep_state = self.condition_query(self.sleep_entity, self.sleep_condition)

        if int(brightness_level) > int(max_brightness_level) and sleep_state != True:
            #If we are above 255 correct for that
            return int(max_brightness_level)
        elif int(brightness_level) < int(min_brightness_level) or sleep_state == True:
            #If we are below min or are in sleep state
            return int(min_brightness_level)
        return brightness_level

    def condition_query (self, entities, condition = None):
        value = False
        condition_states = ['on', 'Home', 'home', 'True', 'true']
        if condition is not None:
            condition_states.append(condition)
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
        """ Change light temp and brightness if conditions are met"""
        #Calculate our percentage and midpoints
        pct, half, midpoint_start, midpoint_end = self.pct()
        #Calculate brightness and temp based on percentage
        brightness_level = self.brightness(pct)
        desired_temp_kelvin, desired_temp_mired = self.color(pct)
        tmp_red, tmp_green, tmp_blue = self.rgb_color(desired_temp_kelvin)
        #Output sensor log
        if 'sensor_log' in self.args:
            sensor_log = self.args['sensor_log']
            # self.set_state(self.args['sensor_log'], state=(pct*100),  attributes = {"unit_of_measurement":"%", "note":"Percentage of dimming, inverted to brightness percent"})
        else:
            sensor_log = 'sensor.' + self.name
        self.set_state(sensor_log, state=(brightness_level/2.55),  attributes = {"unit_of_measurement":"%", "note":"Light brightness", "Kelvin temperature": desired_temp_kelvin, "Mired temperature": desired_temp_mired, "RGB": [tmp_red, tmp_green, tmp_blue], "Midpoint": half, "Start index midpoint": midpoint_start, "End index midpoint": midpoint_end})

        #Check if any disable entities are blocking
        override = self.condition_query(self.disable_entity, self.disable_condition)

        if override or self.sensor_only:
            return None

        #Run companion script if defined
        if 'companion_script' in self.args:
            self.turn_on(entity_id=self.args['companion_script'])
        #Check if sleep conditions are met
        sleep_state = self.condition_query(self.sleep_entity, self.sleep_condition)

        if isinstance(entities, str):
            entities = entities.split(',')
        color_temp_list = []
        kelvin_list = []
        rgb_list = []
        brightness_only_list = []
        """Create service data structures for each light type"""
        rgb_service_data = {"brightness": brightness_level, "transition": transition}
        color_temp_service_data = {"brightness": brightness_level, "transition": transition}
        kelvin_service_data = {"brightness": brightness_level, "transition": transition}
        brightness_only_service_data = {"brightness": brightness_level, "transition": transition}

        for entity_id in entities:
            """Loop through lights, checking the condition for each one. Append each compliant light to a list depending on what type of adjustment the light is capable of."""
            cur_state = self.get_state(entity_id)
            if (cur_state == 'on' or (self.keep_lights_on and self.now_is_between(self.start_time, self.end_time))):
                brightness = self.get_state(entity_id, attribute="brightness")
                if (brightness is not None and (abs(int(brightness) - int(brightness_level)) < int(threshold)) and int(brightness) != int(brightness_level)) or self.keep_lights_on or sleep_state:
                    color_temp = self.get_state(entity_id, attribute='color_temp')
                    kelvin = self.get_state(entity_id, attribute='kelvin')
                    rgb_color = self.get_state(entity_id, attribute='rgb_color')
                    if (rgb_color is not None and color_temp is None and kelvin is None) or (sleep_state == True and rgb_color is not None):
                        rgb_list.append(entity_id)
                    elif color_temp is not None:
                        color_temp_list.append(entity_id)
                    elif kelvin is not None:
                        kelvin_list.append(entity_id)
                    else:
                        brightness_only_list.append(entity_id)

        if len(rgb_list) != 0:
            if sleep_state:
                rgb_service_data['color_name'] = self.sleep_color
            else:
                rgb_service_data['rgb_color'] = [int(tmp_red), int(tmp_green), int(tmp_blue)]
            rgb_service_data['entity_id'] = rgb_list
            self.call_service("light/turn_on", **rgb_service_data)

        if len(color_temp_list) != 0:
            color_temp_service_data['entity_id'] = color_temp_list
            color_temp_service_data['color_temp'] = desired_temp_mired
            self.call_service("light/turn_on", **color_temp_service_data)

        if len(kelvin_list) != 0:
            kelvin_service_data['entity_id'] = kelvin_list
            kelvin_service_data['kelvin'] = desired_temp_kelvin
            self.call_service("light/turn_on", **kelvin_service_data)

        if len(brightness_only_list) != 0:
            brightness_only_service_data['entity_id'] = brightness_only_list
            self.call_service("light/turn_on", **brightness_only_service_data)
