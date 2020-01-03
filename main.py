"""
Author WG 2019
ESP32 Micropython module for a environment sensor.
The MIT License (MIT)
"""
from machine import Timer
import gc
import app
import www

# wait for wifi connection and set RTC from NTP
def record(timer = None):
  import app
  print(app.tm(), "Record timer")
  # record
  app.vals[5] = bat()
  if app.bme is not None: 
    v = app.bme.read()
    app.vals[0] = round(v[0] * app.cfg.cal[0] + app.cfg.dt[0], 1)
    app.vals[1] = round(v[1] * app.cfg.cal[1] + app.cfg.dt[1], 1)
    app.vals[2] = round(v[2] * app.cfg.cal[2] + app.cfg.dt[2], 1)
  if app.lux is not None:
    app.vals[4] = round(app.lux.read() * app.cfg.cal[5] + app.cfg.dt[5], 1)
    if app.vals[4] < 0:
      app.vals[4] = 0
    app.vals[2] = round(app.lux.UV * app.cfg.cal[2] + app.cfg.dt[2], 1)
    if app.vals[2] < 0:
      app.vals[2] = 0
  if app.ds is not None:
    app.vals[3] = round(app.ds.read() * app.cfg.cal[3] + app.cfg.dt[3], 1)
  print(app.tm(), "Readings", app.vals)
  if "http" in app.cfg.url:
    if not app.www.httpsend():
      if time.time() // 60 % 60 == 0:
        app.mem.savemem()
  gosleep()
  
def gosleep():
  from machine import Pin
  import machine
  import time
  import network
  import app
  if app.cfg.slp > 0:
    # power off
    network.WLAN(network.STA_IF).active(False)
    Pin(25, Pin.IN, Pin.PULL_HOLD)
    Pin(15, Pin.IN, Pin.PULL_HOLD)
    Pin(26, Pin.IN, Pin.PULL_HOLD)
    Pin(4, Pin.IN, Pin.PULL_HOLD)
    Pin(16, Pin.IN, Pin.PULL_HOLD)
    Pin(27, Pin.IN, Pin.PULL_HOLD)
    Pin(14, Pin.IN, Pin.PULL_HOLD)
    # time to sleep
    next = (app.cfg.node & 0x07) + 15 + app.cfg.rec * 60 - time.time() % (app.cfg.rec * 60)
    print(app.tm(), "DEEP SLEEP ", next)
    machine.deepsleep(next * 1000)

def waitrst(timer = None):
  """ Timer handler to forcing go sleep """
  import app
  print(app.tm(), app.LIGHTRED, "FORCE sleep or reset", app.END)
  gosleep()

def bat():
  import app
  if app.adc is None:
    return 0
  mx = app.adc.read()
  mn = mx
  s = mx
  for _ in range(11):
    v = app.adc.read()
    s += v
    if v > mx:
      mx = v
    if v < mn:
      mn = v
  s = s - mx - mn
  return int(round(s * 0.176))

def hms(t):
  return "{:2d}:{:02d}:{:02d}".format(t//3600, t//60%60, t%60)

def startup():
    from machine import Pin, ADC, I2C
    import time
    import app
    import mem
    import bme280
    import si1145
    import ds18b20

    # devices and values
    #app.devs = ["BME280","","","DS18B20","Si1145","Vbat"]
    #app.units = ["T1[C]","P[hPa]","H[%]","T2[C]","I[lx]","Vbat[mV]"]

    # led
    if app.cfg.led != 0:
        app.led(app.cfg.led)
    # bat ESP32 Lolin like
    app.adc = ADC(Pin(35))
    app.adc.atten(ADC.ATTN_11DB)
    # rtc mem
    app.mem = mem.MEM()
    # i2c
    Pin(26, Pin.OUT, Pin.PULL_DOWN, value=0)
    Pin(25, Pin.OUT, Pin.PULL_UP, value=1)
    Pin(27, Pin.IN, Pin.PULL_UP)
    Pin(14, Pin.IN, Pin.PULL_UP)
    app.i2c = I2C(scl=Pin(27), sda=Pin(14), freq=400000)
    # bme280
    try:
      app.bme = bme280.BME280(app.i2c)
      app.devs[0] = "BME280"
      app.units[0] = "T1[C]"
      app.units[1] = "P[hPa]"
      app.units[2] = "H[%]"
    except:
      app.bme = None
    # si1145
    try:
      app.lux = si1145.SI1145(app.i2c)
      app.devs[4] = "Si1145"
      app.units[4] = "I[lx]"
      app.units[2] = "UV[]"
    except:
      app.lux = None
    #ds18b20
    Pin(4, Pin.OUT, Pin.PULL_DOWN, value=0)
    Pin(15, Pin.OUT, Pin.PULL_UP, value=1)
    Pin(16, Pin.IN, Pin.PULL_UP)
    try:
      app.ds = ds18b20.DS18B20(16)
      app.devs[3] = "DS18B20"
      app.units[3] = "T2[C]"
    except:
      app.ds = None
    # ntp
    app.ntp(app.cfg.ntp)
    #Vbat
    print(app.tm(), "Node", app.cfg.node, "Vbat", bat())



###############################################################################
# MAIN
###############################################################################

app.VERSION = "D32-UV-200103"

timer1 = Timer(1)
timer1.init(period=12000, mode=Timer.ONE_SHOT, callback=waitrst)

startup()
app.www = www.WWW(True)

record()

timer2 = Timer(2)
timer2.init(period=60*1000*app.cfg.rec, mode=Timer.PERIODIC, callback=record)

gc.enable()
#app.www.extparse = parse
#app.www.exthandle = handle
