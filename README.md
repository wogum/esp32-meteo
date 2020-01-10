# ESP32 MicroPython Meteo Station

ESP32 meteo station

Autodetects devices: 
 * BME280 - I2C temperature, pressure and humidity sensor
 * DH18B20 - OneWire temperature sensor
 * MX44009 - I2C light lux calibrated illumination sensor
 * Si1145 - I2C light sensor with UV factor

Battery voltage on pin35 via 100k/100k divider like in Wemos Lolin D32

Attention: LED Pin varing module to module, 
for example NodeMCU aka Dev.C uses pin 2 with positive logic, 
Wemos Lolin Lite uses pin 22 with negative logic,
Wemos Lolin D32 and D32 Pro uses pin 5 with negative logic,
new ESP8266 modules uses pin 2 with negative logic.

Remember to set proper pin numbers in config.py 

maind1.py is main.py for ESP8266 with limited functionality - no www server and no light sensors.
