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
  app.vals[5] = int(bat() * app.cfg.cal[5] + app.cfg.dt[5])
  if app.bme is not None: 
    try:
      v = app.bme.read()
    except:
      v = (0, 0, 0)
    for i in range(3):
      app.vals[i] = round(v[i] * app.cfg.cal[i] + app.cfg.dt[i], 1)
  if app.lux is not None:
    try:
      app.vals[4] = round(app.lux.read() * app.cfg.cal[4] + app.cfg.dt[4], 1)
    except:
      pass
    if app.vals[4] < 0:
      app.vals[4] = 0
    if 'Si1145' in app.devs:
      try:
        app.vals[2] = round(10*app.lux.UV * app.cfg.cal[2] + app.cfg.dt[2], 1)
      except:
        pass
      if app.vals[2] < 0:
        app.vals[2] = 0
  if app.ds is not None:
    try:
      app.vals[3] = round(app.ds.read() * app.cfg.cal[3] + app.cfg.dt[3], 1)
    except:
      pass
    if app.devs[0] == '' and app.vals[0] == 0 and app.vals[3] != 0:
      app.vals[0] = app.vals[3]
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
    if not app.www.httpsend(hist):
      if hist:
        v = app.mem.savemem()
        print(app.tm(), "Save to mem: ", v)
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
    for pin in (25,15,26,4,16,27,14):
      Pin(pin, Pin.IN, Pin.PULL_HOLD)
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
  return int(round(s * 0.176))

def startup():
    from machine import Pin, ADC, I2C
    import time
    import app
    import mem
    import bme280
    import si1145
    import ds18b20
    import www

    # devices and values
    #app.devs = ["BME280","","","DS18B20","Si1145","Vbat"]
    #app.units = ["T1[C]","P[hPa]","H[%]","T2[C]","I[lx]","Vbat[mV]"]

    # led
    if app.cfg.led != 0:
        app.led(app.cfg.led)
    # bat ESP32 Lolin D32 like Vbat 100k/100k
    app.adc = ADC(Pin(35))
    app.adc.atten(ADC.ATTN_11DB)
    app.adc.width(ADC.WIDTH_12BIT)
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
      app.units[0] = "T[C]"
      app.units[1] = "P[hPa]"
      app.units[2] = "H[%]"
    except:
      app.bme = None
    # si1145 / max44009
    try:
      app.lux = si1145.SI1145(app.i2c)
      app.devs[4] = "Si1145"
      app.units[4] = "E[lx]"
      app.units[2] = "UV[%]"
    except:
      app.lux = None
    if app.lux is None:
      try:
        import max44009
        app.lux = max44009.MAX44009(app.i2c)
        app.devs[4] = "Max44009"
        app.units[4] = "E[lx]"
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
    # www
    app.www = www.WWW(True)
    #Vbat
    print(app.tm(), app.VERSION, "Node", app.cfg.node, app.cfg.hostname, "Vbat", bat())
    print(app.tm(), app.devs)
    print(app.tm(), app.units)



###############################################################################
# MAIN
###############################################################################

app.VERSION = "D32-200105"

timer1 = Timer(1)
timer1.init(period=12000, mode=Timer.ONE_SHOT, callback=gosleep)

startup()

record()

timer2 = Timer(2)
timer2.init(period=60*1000*app.cfg.rec, mode=Timer.PERIODIC, callback=record)

gc.enable()
