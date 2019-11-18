# Northcliff Home Manager Display
This project uses a Raspberry Pi and a SenseHat to monitor and display the states of key sensors that are being managed by the [Northcliff Home Manager](https://github.com/roscoe81/Home-Manager). It provides an "at a glance" view of the key property sensor states.

The SenseHat mimics the managed property's layout to display the following sensor states:
### Indoor and Outdoor Motion Sensors
  Motion Detected is indicated by a red pixel.
### Indoor and Outdoor Temperature Sensors
  Indoor and Outdoor temperatures are calibrated with different ranges and the relevant pixels change shades from blue to green to red as the temperature increases.
### Outdoor Humidity Sensors
  The relevant pixel changes from red to green to blue as the humidity increases.
### Indoor Air Quality Levels
  The relevant pixel changes from green to red as the air quality deteriorates. There is also a pixel that is red when the BlueAir filter needs changing.
### Airconditioner Heating/Cooling/Fan States and Filter Status
  The relevant aircon state pixel is orange for heat, cyan for cool and white for fan mode. A second pixel is set to red if the aircon filter requires cleaning.
### Door Sensors
The relevant pixel is green for door closed and yellow for door opened.
### Aquarium ph Sensor
The relevant pixel is red for a ph <= 6.5, green for a ph of 7 and blue for a ph >= 7.5, with proportional hues between those levels.
### Aquarium nh3 Sensor
The relevant pixel is green for an nh3 level of 0ppm, yellow for 0.1ppm and red for >= 0.2ppm, with proportional hues between those levels.
### Aquarium Temperature Sensor
The relevant pixel is red for a temperature >= 28 degrees Celsius, green for a temperature of 25 degrees Celsius and blue for a temperature <= 22 degrees Celsius, with proportional hues between those levels.

One of Home Manager's light level sensors is monitored to dim the SenseHat's display during low light conditions.

The Home Manager sensor states are determined by monitoring the mqtt messages between the Home Manager and Homebridge or the Home Manager and Domoticz.

This project also uses SenseHat's air pressure monitor to record air pressure pressure changes over a 3 hour period to make some weather predictions. It uses five pixels as follows:
### Wind Prediction
  The pixel is white for No Change and is set to a shade of red, depending on the likelihood of wind.
### Rain Prediction
  The pixel is white for No Change and is set to a shade of blue, depending on the likelihood of rain.
### Temperature Prediction
  The pixel is white for No Change and is set to a shade of blue or red, depending on the likely temperature movement (blue for decreasing and red for increasing.
### Current Air Pressure
  The pixel changes from shades of blue to green to red as the air pressure increases.
### Air Pressure Change Over Past 3 Hours
  The pixel is set to shades of blue for falling air pressures, green for no change and red for increasing air pressures.

I have used systemd to execute the code on boot and automatically restart on errors, as well as using the Raspberry Pi watchdog timer. These improve system reliability.

![Northcliff Home Manager Display](https://github.com/roscoe81/Home-Manager-Display/blob/master/IMG_6003.jpg)

## License

This project is licensed under the MIT License - see the LICENSE.md file for details
