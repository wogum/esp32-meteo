"""
Author WG 2019
ESP32 Micropython module for a environment sensor.
The MIT License (MIT)
"""
from machine import Timer
import gc
import app

# wait for wifi connection and set RTC from NTP
def record(timer = None):
  import time
  import app
  print(app.tm(), "Readings")
  # record
  # Vbat
  app.vals[5] = int(bat() * app.cfg.cal[5] + app.cfg.dt[5])
  # TPH
  if app.bme is not None: 
    try:
      v = app.bme.read()
    except:
      v = (0, 0, 0)
    for i in range(3):
      app.vals[i] = round(v[i] * app.cfg.cal[i] + app.cfg.dt[i], 1)
  # T2
  if app.ds is not None:
    try:
      v = app.ds.read()
      if app.devs[0] == "" or app.devs[0] == "DS18B20":
        app.devs[0] = "DS18B20"
        app.vals[0] = round(v * app.cfg.cal[0] + app.cfg.dt[0], 1)
      else:
        app.vals[3] = round(v * app.cfg.cal[3] + app.cfg.dt[3], 1)
    except:
      pass
  print(app.tm(), "Values: ", app.vals)
  # sync time
  if app.ntp(app.cfg.ntp):
    # sleep correction
    next = app.cfg.rec * 60 - time.time() % (app.cfg.rec * 60)
    if next < 30:
      print(app.tm(), "Sleep correction", next)
      gosleep()
  # http send
  if "http" in app.cfg.url:
    hist = (((time.time() + 60) // 60) % 60) <= 1
    if app.www.httpsend(hist):
      print(app.tm(), app.GREEN, "HTTP sent", app.END)
    else:
      if hist:
        try:
          v = app.mem.savemem()
          print(app.tm(), "Saved to mem: ", v)
        except:
          pass
  gosleep()
  
def gosleep(timer = None):
  from machine import Pin
  import machine
  import time
  import network
  import app
  if timer is not None:
    print(app.tm(), app.LIGHTRED, "FORCE sleep", app.END)
  if app.cfg.slp > 0:
    # power off
    network.WLAN(network.STA_IF).active(False)
    # time to sleep
    next = (app.cfg.node & 0x07) + 15 + app.cfg.rec * 60 - time.time() % (app.cfg.rec * 60)
    print(app.tm(), app.RED, "Deep sleep ", app.END, next)
    machine.deepsleep(next * 1000)

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
  return int(round(s * 0.573))

def startup():
    from machine import Pin, ADC, I2C
    import app
    import ds18b20
    import www

    # devices and values
    #app.devs = ["BME280","","","DS18B20","Si1145","Vbat"]
    #app.units = ["T1[C]","P[hPa]","H[%]","T2[C]","I[lx]","Vbat[mV]"]

    # led
    if app.cfg.led != 0:
        app.led(app.cfg.led)
    # bat ESP32 Lolin D32 like Vbat 100k/100k
    app.adc = ADC(0)
    app.bme = None
    app.lux = None
    app.mem = None
    app.ds = None
    # i2c
    Pin(14, Pin.OUT, Pin.PULL_UP, value=1)
    Pin(4, Pin.IN, Pin.PULL_UP)
    Pin(5, Pin.IN, Pin.PULL_UP)
    app.i2c = I2C(scl=Pin(5), sda=Pin(4), freq=400000)
    s = app.i2c.scan()
    if 0x76 in s or 0x77 in s:
      import bme280
      # bme280
      try:
        app.bme = bme280.BME280(app.i2c)
        app.devs[0] = "BME280"
        app.units[0] = "T[C]"
        app.units[1] = "P[hPa]"
        app.units[2] = "H[%]"
      except:
        app.bme = None
    #ds18b20
    Pin(15, Pin.OUT, value=0)
    Pin(13, Pin.OUT, Pin.PULL_UP, value=1)
    Pin(12, Pin.IN, Pin.PULL_UP)
    try:
      app.ds = ds18b20.DS18B20(12)
      if app.devs[0] == "":
        app.devs[0] = "DS18B20"
        app.units[0] = "T[C]"
      else:
        app.devs[3] = "DS18B20"
        app.units[3] = "T2[C]"
    except:
      app.ds = None
    # www
    app.www = www.WWW(False)
    #Vbat
    print(app.tm(), app.VERSION, "Node", app.cfg.node, app.cfg.hostname, "Vbat", bat())
    print(app.tm(), app.devs)
    print(app.tm(), app.units)



###############################################################################
# MAIN
###############################################################################

app.VERSION = "D32-200110"
gc.enable()

timer1 = Timer(1)
timer1.init(period=12000, mode=Timer.ONE_SHOT, callback=gosleep)

startup()

record()

timer2 = Timer(2)
timer2.init(period=60*1000*app.cfg.rec, mode=Timer.PERIODIC, callback=record)

#app.www.server()
