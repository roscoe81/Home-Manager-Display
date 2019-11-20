#!/usr/bin/env python3
# Northcliff Home Manager Display - Version 3.15 Gen
# Requires Home Manager >= Version 8.14
import time
import paho.mqtt.client as mqtt
import json
from datetime import datetime
from sense_hat import SenseHat


class NorthcliffDisplay(object): # The class for the main display code
    def __init__(self):
        self.homebridge_outgoing_mqtt_topic='homebridge/to/set'
        self.domoticz_incoming_mqtt_topic='domoticz/in'
        self.multisensor_names = ['Living', 'Study', 'Kitchen', 'North', 'South', 'Main', 'Rear Balcony', 'North Balcony', 'South Balcony']
        self.motion_map={'Living Motion':(6,4), 'Study Motion':(2,3), 'Kitchen Motion':(3,0), 'North Motion':(1,6), 'South Motion':(1,0), 'Main Motion':(5,6),
                          'Rear Balcony Motion':(0,6), 'North Balcony Motion':(7,6), 'South Balcony Motion':(7,0)}
        self.door_map={'Entry Door':(3,7), 'South Living Room Door':(7,3), 'North Living Room Door':(7,4)}
        self.temp_map={'Living Temperature':(6,5), 'Study Temperature':(2,4), 'Kitchen Temperature':(3,1), 'North Temperature':(1,7), 'South Temperature':(1,1), 'Main Temperature':(5,7),
                          'Rear Balcony Temperature':(0,7), 'North Balcony Temperature':(7,7), 'South Balcony Temperature':(7,1)}
        self.display_buffer=[[0,0,0] for a in range(64)]
        self.aircon_state_map=(4,4)
        self.aircon_filter_map=(4,5)
        self.hum_map=(7,5)
        self.aqi_map=(4,2)
        self.air_purifier_filter_map={'Living Air Purifier':(4,3), 'Main Air Purifier':(6,6)}
        self.barometer_map=(0,3)
        self.barometer_calibration_offset=-3
        self.barometer_change_map=(0,4)
        self.barometer_history = [0.00 for x in range (10)]
        self.weather_forecast=[[0,0],[0,0],[0,0]]
        self.wind_forecast_map=(0,0)
        self.rain_forecast_map=(0,1)
        self.temp_forecast_map=(0,2)
        self.forecast_barometer_map={'No Change':[[[120,0],[120,0],[120,0]],'0'], 'Clearing and Colder':[[[120,100],[120,100],[180,100]],'0'], 'Rain and Wind':[[[60,100],[240,100],[120,0]],'3'], 'Storm':[[[30,100],[240,100],[180,100]],'4'],
                                      'Storm and Gale':[[[0,100],[240,100],[180,100]],'4'], 'Strong Wind Warning':[[[30,100],[120,0],[120,0]],'3'], 'Gale Warning': [[[0,100],[120,0],[120,0]],'4'],
                                      'Poorer Weather': [[[60,100],[180,100],[180,100]],'3'],
                                      'Fair Weather with Slight Temp Change': [[[120,100],[120,100],[150,100]],'1'], 'No Change and Rain in 24 Hours': [[[120,0],[180,100],[120,0]],'3'],
                                      'Rain, Wind and Higher Temp': [[[80,100],[180,100],[60,100]],'3'],
                                      'Fair Weather':[[[120,100],[120,100],[120,100]],'1'], 'Fair Weather Weather with No Marked Temp Change': [[[120,100],[120,100],[120,0]],'0'],
                                      'Fair Weather and Slowly Rising Temp': [[[120,100],[120,100],[60,100]],'1'], 'Warming Trend': [[[120,0],[120,0],[30,100]],'1']}
        self.domoticz_barometer_format={'idx':767,'nvalue':0}
        self.domoticz_barometer_level='0'
        self.domoticz_barometer_forecast='0'
        self.aquarium_ph_map=(5,0)
        self.aquarium_nh3_map=(5,1)
        self.aquarium_temp_map=(5,2)
        self.aquarium_idx_map={'ph':769,'nh3':770,'temp':772}
        self.low_light=False
     
    def on_connect(self, client, userdata, flags, rc):
        # Sets up the mqtt subscriptions. Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.
        self.print_update('Northcliff Home Manager Display Connected with result code '+str(rc)+' on ')
        client.subscribe(self.homebridge_outgoing_mqtt_topic) # Subscribe to mqtt messages from Home Manager to Homebridge
        client.subscribe(self.domoticz_incoming_mqtt_topic) # Subscribe to mqtt messages from Home Manager to Domoticz
    
    def on_message(self, client, userdata, msg):
        # Calls the relevant methods for the display, based on the mqtt publish messages received from the Home Manager
        decoded_payload = str(msg.payload.decode("utf-8"))
        parsed_json = json.loads(decoded_payload)
        if msg.topic == self.homebridge_outgoing_mqtt_topic: # If it's a Homebridge message coming from Home Manager
            #print(parsed_json)
            if 'Air Purifier' in parsed_json['name'] and parsed_json['characteristic']=='FilterChangeIndication':
                self.process_air_purifier_filter(parsed_json)
            elif 'Air Quality' in parsed_json['name'] and parsed_json['characteristic']=='AirQuality':
                self.process_aqi(parsed_json)
            elif 'Aircon' in parsed_json['name']:
                self.process_aircon(parsed_json)
            elif parsed_json['service']=='MotionSensor' and parsed_json['characteristic']=='MotionDetected':
                self.process_motion(parsed_json)
            elif parsed_json['service']=='ContactSensor' and parsed_json['characteristic']=='ContactSensorState':
                self.process_door(parsed_json)
            elif parsed_json['service']=='TemperatureSensor' and parsed_json['characteristic']=='CurrentTemperature':
                self.process_temp(parsed_json)
            elif parsed_json['service']=='HumiditySensor' and parsed_json['characteristic']=='CurrentRelativeHumidity':
                self.process_hum(parsed_json)
            elif parsed_json['service_name']=='Living Lux' and parsed_json['characteristic']=='CurrentAmbientLightLevel':
                self.process_lux(parsed_json)
            else:
                #print("Ignored json", parsed_json)
                pass
        elif msg.topic == self.domoticz_incoming_mqtt_topic: # If it's a message sent to Domoticz
            #print('Received Domoticz In Message', parsed_json)
            aquarium_idx_found=False
            for sensor in self.aquarium_idx_map:
                if parsed_json['idx']==self.aquarium_idx_map[sensor]:
                    aquarium_idx_found=True
            if aquarium_idx_found:
                self.process_aquarium(parsed_json)
        else:
            pass # Ignore other messages    

    def process_air_purifier_filter(self, parsed_json):
        if parsed_json['value']==1: # Filter needs changing
            self.load_display_buffer(self.air_purifier_filter_map[parsed_json['name']][0], self.air_purifier_filter_map[parsed_json['name']][1], [0,100,100]) # Red
        else: # Filter is OK
            self.load_display_buffer(self.air_purifier_filter_map[parsed_json['name']][0], self.air_purifier_filter_map[parsed_json['name']][1], [0,0,0]) # Off                                                   

    def process_aircon(self, parsed_json):
        #print("Process Aircon", parsed_json)
        if parsed_json['service_name'] == 'Remote Operation' and parsed_json['value'] == False:
            #print('Aircon Off', self.aircon_state_map[0], self.aircon_state_map[1])
            self.load_display_buffer(self.aircon_state_map[0], self.aircon_state_map[1], [0,0,0]) # Off
        elif parsed_json['service_name'] == 'Fan' and parsed_json['value'] == True:
            #print('Aircon Fan', self.aircon_state_map[0], self.aircon_state_map[1])
            self.load_display_buffer(self.aircon_state_map[0], self.aircon_state_map[1], [0,0,100] ) # White
        elif parsed_json['service_name'] == 'Heat'and parsed_json['value'] == True:
            #print('Aircon Heat', self.aircon_state_map[0], self.aircon_state_map[1])
            self.load_display_buffer(self.aircon_state_map[0], self.aircon_state_map[1], [30,100,100]) # Orange
        elif parsed_json['service_name'] == 'Cool' and parsed_json['value'] == True:
            #print('Aircon Cool', self.aircon_state_map[0], self.aircon_state_map[1])
            self.load_display_buffer(self.aircon_state_map[0], self.aircon_state_map[1], [180,100,100]) # Cyan
        elif parsed_json['service_name']=='Filter' and parsed_json['value']==True:
            #print('Aircon Filter Alarm', parsed_json, self.aircon_filter_map[0], self.aircon_filter_map[1])
            self.load_display_buffer(self.aircon_filter_map[0], self.aircon_filter_map[1], [0,100,100]) # Red
        elif parsed_json['service_name']=='Filter' and parsed_json['value']==False:
            #print('Aircon Filter OK', parsed_json, self.aircon_filter_map[0], self.aircon_filter_map[1])
            self.load_display_buffer(self.aircon_filter_map[0], self.aircon_filter_map[1], [0,0,0]) # Off
        else:
            pass

    def process_motion(self, parsed_json):
        #print('Motion', parsed_json['service_name'], self.motion_map[parsed_json['service_name']][0], self.motion_map[parsed_json['service_name']][1], parsed_json['value'])
        if parsed_json['value'] == True:
            self.load_display_buffer(self.motion_map[parsed_json['service_name']][0], self.motion_map[parsed_json['service_name']][1], [0,100,100]) # Red
        else:
            self.load_display_buffer(self.motion_map[parsed_json['service_name']][0], self.motion_map[parsed_json['service_name']][1], [0,0,0]) # Off

    def process_door(self, parsed_json):
        #print('Door', parsed_json, self.door_map[parsed_json['service_name']][0], self.door_map[parsed_json['service_name']][1])
        if parsed_json['value'] == 1:
            self.load_display_buffer(self.door_map[parsed_json['service_name']][0], self.door_map[parsed_json['service_name']][1], [60,100,100]) # Yellow
        else:
            self.load_display_buffer(self.door_map[parsed_json['service_name']][0], self.door_map[parsed_json['service_name']][1], [120,100,100]) # Green
            
    def process_temp(self, parsed_json):
        #print('Temperature', parsed_json)
        if parsed_json['name']=='Balconies':
            if parsed_json['value']>30:
                hue=0
            elif parsed_json['value']<10:
                hue=240
            else:
                hue=int((30-parsed_json['value'])*12)
        else:
            if parsed_json['value']>26:
                hue=0
            elif parsed_json['value']<18:
                hue=240
            else:
                hue=int((26-parsed_json['value'])*30)
        self.load_display_buffer(self.temp_map[parsed_json['service_name']][0], self.temp_map[parsed_json['service_name']][1], [hue,100,100])

    def process_hum(self, parsed_json):
        if parsed_json['service_name']=='North Balcony Humidity':
            #print('Humidity', parsed_json, self.hum_map[0], self.hum_map[1])
            hue=int(parsed_json['value']*2.4)
            self.load_display_buffer(self.hum_map[0], self.hum_map[1], [hue,100,100])
            
    def process_aqi(self, parsed_json):
        #print('Process Air Quality', parsed_json, self.aqi_map[0], self.aqi_map[1])
        hue=int((5-parsed_json['value'])*30)
        self.load_display_buffer(self.aqi_map[0], self.aqi_map[1], [hue,100,100])

    def process_lux(self, parsed_json):
        #print('Living Light Level', parsed_json)
        if parsed_json['value']<40:
            self.low_light=True
        else:
            self.low_light=False

    def process_barometer(self):
        barometer_log_time = time.time()
        barometer=round(sense.get_pressure(),2)+self.barometer_calibration_offset
        if barometer>500: # Only record valid barometer readings. Caters for startup mode
            valid_barometer_reading=True
            valid_barometer_history, barometer_change = self.log_barometer(barometer)
            self.print_update('Barometer Reading of '+str(barometer)+' millibars on ')
            if barometer>1023:
                hue=0
            elif barometer<1003:
                hue=240
            else:
                hue=int((1023-barometer)*12)
            self.load_display_buffer(self.barometer_map[0], self.barometer_map[1], [hue,100,100])
            self.domoticz_barometer=str(round(barometer,1))
            if valid_barometer_history == True:
                self.process_barometer_change(barometer_change, barometer)
            else:
                domoticz_json = self.domoticz_barometer_format
                domoticz_json['svalue'] = self.domoticz_barometer+';0'
                client.publish(self.domoticz_incoming_mqtt_topic, json.dumps(domoticz_json))
        else:
            valid_barometer_reading=False
        return valid_barometer_reading, barometer_log_time

    def process_aquarium(self,parsed_json):
        print('Aquarium Message', parsed_json)
        if parsed_json['idx']==self.aquarium_idx_map['ph']:
            print('ph:', parsed_json['svalue'], self.aquarium_ph_map[0], self.aquarium_ph_map[1])
            ph=float(parsed_json['svalue'])
            if ph<6.5:
                hue=0
            elif ph>7.5:
                hue=240
            else:
                hue=int((ph-6.5)*240)
            self.load_display_buffer(self.aquarium_ph_map[0], self.aquarium_ph_map[1], [hue,100,100])
        elif parsed_json['idx']==self.aquarium_idx_map['nh3']:
            print('nh3:', parsed_json['svalue'], self.aquarium_nh3_map[0], self.aquarium_nh3_map[1])
            nh3=float(parsed_json['svalue'])
            if nh3<0:
                hue=120
            elif nh3>0.2:
                hue=0
            else:
                hue=int(120-nh3*600)
            self.load_display_buffer(self.aquarium_nh3_map[0], self.aquarium_nh3_map[1], [hue,100,100])
        elif parsed_json['idx']==self.aquarium_idx_map['temp']:
            print('temp:', parsed_json['svalue'], self.aquarium_temp_map[0], self.aquarium_temp_map[1])
            temp=float(parsed_json['svalue'])
            if temp<22:
                hue=240
            elif temp>28:
                hue=0
            else:
                hue=int((temp-28)*-40)
            self.load_display_buffer(self.aquarium_temp_map[0], self.aquarium_temp_map[1], [hue,100,100])
        else:
            pass
            
    def log_barometer(self, barometer): # Logs 3 hours of barometer readings, taken every 18 minutes
        three_hour_barometer=self.barometer_history[9] # Capture barometer reading from 3 hours ago
        for pointer in range (9, 0, -1): # Move previous temperatures one position in the list to prepare for new temperature to be recorded
            self.barometer_history[pointer] = self.barometer_history[pointer - 1]
        self.barometer_history[0] = barometer # Log latest reading
        if three_hour_barometer!=0:
            valid_barometer_history = True
            barometer_change = barometer - three_hour_barometer
        else:
            valid_barometer_history=False
            barometer_change = 0
        #self.print_update("Log Barometer on ")
        #print("Result", self.barometer_history,valid_barometer_history, round(barometer_change,2))
        return valid_barometer_history, barometer_change

    def process_barometer_change(self, barometer_change, barometer):
        if barometer_change>4:
            hue=0
        elif barometer_change<-4:
            hue=240
        else:
            hue=int(120-barometer_change*30)
        self.load_display_buffer(self.barometer_change_map[0], self.barometer_change_map[1], [hue,100,100])
        led_forecast, forecast, domoticz_forecast = self.analyse_barometer(barometer_change, barometer, self.forecast_barometer_map)
        self.load_display_buffer(self.wind_forecast_map[0], self.wind_forecast_map[1], [led_forecast[0][0],led_forecast[0][1],100])
        self.load_display_buffer(self.rain_forecast_map[0], self.rain_forecast_map[1], [led_forecast[1][0],led_forecast[1][1],100])
        self.load_display_buffer(self.temp_forecast_map[0], self.temp_forecast_map[1], [led_forecast[2][0],led_forecast[2][1],100])
        self.domoticz_barometer_forecast=domoticz_forecast
        domoticz_json = self.domoticz_barometer_format
        domoticz_json['svalue'] = self.domoticz_barometer +';'+self.domoticz_barometer_forecast
        client.publish('domoticz/in', json.dumps(domoticz_json))
        self.print_update('3 hour barometer change is '+str(round(barometer_change,1))+' millibars with a current reading of '+str(round(barometer,1))+' millibars. The weather forecast is "'+forecast+'" on ') 

    def analyse_barometer(self, barometer_change, barometer, forecast_barometer_map):
        led_forecast=[[0,0],[0,0],[0,0]]
        if barometer<1009:
            if barometer_change>-1.1 and barometer_change<6:
                forecast = 'Clearing and Colder'
            elif barometer_change>=6 and barometer_change<10:
                forecast = 'Strong Wind Warning'
            elif barometer_change>=10:
                forecast = 'Gale Warning'
            elif barometer_change<=-1.1 and barometer_change>=-4:
                forecast = 'Rain and Wind'
            elif barometer_change<-4 and barometer_change>-10:
                forecast = 'Storm'
            else:
                forecast = 'Storm and Gale'
        elif barometer>=1009 and barometer <=1018:
            if barometer_change>-4 and barometer_change<1.1:
                forecast = 'No Change'
            elif barometer_change>=1.1 and barometer_change<=6 and barometer<=1015:
                forecast = 'No Change'
            elif barometer_change>=1.1 and barometer_change<=6 and barometer>1015:
                forecast = 'Poorer Weather'
            elif barometer_change>=6 and barometer_change<10:
                forecast = 'Strong Wind Warning'
            elif barometer_change>=10:
                forecast = 'Gale Warning'       
            else:
                forecast = 'Rain and Wind'
        elif barometer>1018 and barometer <=1023:
            if barometer_change>0 and barometer_change<1.1:
                forecast = 'No Change'
            elif barometer_change>=1.1 and barometer_change<6:
                forecast = 'Poorer Weather'
            elif barometer_change>=6 and barometer_change<10:
                forecast = 'Strong Wind Warning'
            elif barometer_change>=10:
                forecast = 'Gale Warning'
            elif barometer_change>-1.1 and barometer_change<=0:
                forecast = 'Fair Weather with Slight Temp Change'
            elif barometer_change<=-1.1 and barometer_change>-4:
                forecast = 'No Change and Rain in 24 Hours'
            else:
                forecast = 'Rain, Wind and Higher Temp'
        else: # barometer>1023
            if barometer_change>0 and barometer_change<1.1:
                forecast = 'Fair Weather'
            elif barometer_change>-1.1 and barometer_change<=0:
                forecast = 'Fair Weather Weather with No Marked Temp Change'
            elif barometer_change>=1.1 and barometer_change<6:
                forecast = 'Poorer Weather'
            elif barometer_change>=6 and barometer_change<10:
                forecast = 'Strong Wind Warning'
            elif barometer_change>=10:
                forecast = 'Gale Warning'    
            elif barometer_change<=-1.1 and barometer_change>-4:
                forecast = 'Fair Weather and Slowly Rising Temp'
            else:
                forecast = 'Warming Trend'
        led_forecast=forecast_barometer_map[forecast][0]
        domoticz_forecast=forecast_barometer_map[forecast][1]
        return led_forecast, forecast, domoticz_forecast

    def load_display_buffer(self,x,y,h_s_v):
        red,green,blue=self.set_led_colour(h_s_v[0], h_s_v[1], h_s_v[2])
        #print("Display Buffer Update", x, y, "HSV:", h_s_v, "RGB", (red,green,blue))
        self.display_buffer[x+y*8]=(red,green,blue)

    def drive_display(self):
        sense.low_light=self.low_light
        sense.set_pixels(self.display_buffer)                                

    def set_led_colour(self, hue_value, saturation_value, brightness):
        c_value = (brightness/100) * (saturation_value/100)
        x_value = c_value * (1-abs((hue_value/60) % 2 - 1))
        m_value = brightness/100 - c_value
        if (hue_value >= 0 and hue_value < 60):
            red_value = c_value
            green_value = x_value
            blue_value = 0
        elif (hue_value >= 60  and hue_value < 120):
            red_value = x_value
            green_value = c_value
            blue_value = 0
        elif (hue_value >= 120  and hue_value < 180):
            red_value = 0
            green_value = c_value
            blue_value = x_value
        elif (hue_value >= 180  and hue_value < 240):
            red_value = 0
            green_value = x_value
            blue_value = c_value
        elif (hue_value >= 240  and hue_value < 300):
            red_value = x_value
            green_value = 0
            blue_value = c_value
        elif (hue_value >= 300  and hue_value < 360):
            red_value = c_value
            green_value = 0
            blue_value = x_value
        else:
            pass
        red = int((red_value + m_value) * 255)
        green = int((green_value + m_value) * 255)
        blue = int((blue_value + m_value) * 255)
        #print(red,green,blue)
        return red,green,blue

    def print_update(self, print_message): # Prints with a date and time stamp
        today = datetime.now()
        print(print_message + today.strftime('%A %d %B %Y @ %H:%M:%S'))
         
    def shutdown_cleanup(self):
        sense.clear()
        client.loop_stop() # Stop mqtt monitoring
        self.print_update("Northcliff Home Manager Display stopped on ")
        
    def run(self):
        self.print_update("Northcliff Home Manager Display started on ")
        try:
            valid_barometer_reading=False
            while valid_barometer_reading==False: # Wait for valid barometer reading
                valid_barometer_reading, barometer_log_time = self.process_barometer()
            while True: # Run display in continuous loop
                time.sleep(0.5)
                self.drive_display()
                if (time.time() - barometer_log_time) >= 1080: # Update the barometer log if last update was >= 18 minutes ago
                    valid_barometer_reading, barometer_log_time = self.process_barometer()     
        except KeyboardInterrupt: # Shutdown on ctrl C
            # Shutdown main program
            print('Barometer Log:', self.barometer_history)
            self.shutdown_cleanup()
            
if __name__ == '__main__': # This is where to overall code kicks off
    sense = SenseHat()
    sense.set_rotation(180)
    sense.clear()
    # Create a Home Manager Display instance
    dsp = NorthcliffDisplay()
    # Create and set up an mqtt instance                             
    client = mqtt.Client('home_manager_display')
    client.on_connect = dsp.on_connect
    client.on_message = dsp.on_message
    client.connect("mqtt broker name>", 1883, 60)
    # Blocking call that processes network traffic, dispatches callbacks and handles reconnecting.
    client.loop_start()
    dsp.run()







        
