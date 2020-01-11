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
      if len(v) < 3:
        v.append(0)
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
      v = app.ds.read()
      if app.devs[0] == "" or app.devs[0] == "DS18B20":
        app.devs[0] = "DS18B20"
        app.vals[0] = round(v * app.cfg.cal[0] + app.cfg.dt[0], 1)
      else:
        app.vals[3] = round(v * app.cfg.cal[3] + app.cfg.dt[3], 1)
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
      if hist and app.mem is not None:
        v = app.mem.savemem()
        print(app.tm(), "Save to mem: ", v)
  gosleep()
  # if not going sleep then start BLE advertising
  bleadvert(app.vals[0] if app.units[0].startswith('T') else 0, 
    app.vals[1] if app.units[1].startswith('P') else 0, 
    app.vals[2] if app.units[2].startswith('H') else 0)

# start BLE advertising T, P and H in iNode PTH format
def bleadvert(t,p,h):
  import struct
  import time
  import ubluetooth
  import app
  if app.ble is None:
    app.ble = ubluetooth.BLE()
    app.ble.active(True)
  epoch = int(time.time() + 946684800)
  resp = b'\x0a\x09' + "ESP32 PTH" #+ b'\x02\x0A\x08'
  adv = (b'\x02\x01\x06\x19\xFF\x10\x9D\x00\xF0\x00\x00' +
    struct.pack('<HHHHH', int(16*p), int((t+46.85)/175.72*16384), int((h+6)/125*16384), epoch >> 16, epoch & 0xFFFF) +
    b'\x00\x00\x00\x00\x00\x00\x00\x00')
  app.ble.gap_advertise(1000000, adv, resp_data = resp)

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
    app.bme = None
    app.lux = None
    app.ds = None
    app.ble = None
    s = app.i2c.scan()
    # bme280/bmp280/bmp180/bmp085
    if 0x76 in s or 0x77 in s:
      if 0x76 in s:
        addr = 0x76
      else:
        addr = 0x77
      try:
        id = app.i2c.readfrom_mem(addr, 0xD0, 1)[0]
      except:
        id = 0
      if id == 0x55:
        try:
          import bmp180
          app.bme = bmp180.BMP180(app.i2c)
          app.devs[0] = "BMP180"
          app.units[0] = "T[C]"
          app.units[1] = "P[hPa]"
        except:
          app.bme = None
      elif id == 0x58 or id == 0x60:  
        try:
          import bme280
          app.bme = bme280.BME280(app.i2c)
          app.devs[0] = "BMP280"
          app.units[0] = "T[C]"
          app.units[1] = "P[hPa]"
          if id == 0x60:
            app.devs[0] = "BME280"
            app.units[2] = "H[%]"
        except:
          app.bme = None
      else:
        app.bme = None
    # si1145 / max44009
    if 0x60 in s:
      try:
        import si1145
        app.lux = si1145.SI1145(app.i2c)
        app.devs[4] = "Si1145"
        app.units[4] = "E[lx]"
        app.units[2] = "UV[%]"
      except:
        app.lux = None
    if app.lux is None and (0x4A in s or 0x4B in s):
      try:
        import max44009
        app.lux = max44009.MAX44009(app.i2c)
        app.devs[4] = "Max44009"
        app.units[4] = "E[lx]"
      except:
        app.lux = None
    Pin(4, Pin.OUT, Pin.PULL_DOWN, value=0)
    Pin(15, Pin.OUT, Pin.PULL_UP, value=1)
    Pin(16, Pin.IN, Pin.PULL_UP)
    #ds18b20
    try:
      app.ds = ds18b20.DS18B20(16)
      if app.devs[0] == "":
        app.devs[0] = "DS18B20"
        app.units[0] = "T[C]"
      else:
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

app.VERSION = "D32-200110"

timer1 = Timer(1)
timer1.init(period=12000, mode=Timer.ONE_SHOT, callback=gosleep)

startup()

record()

timer2 = Timer(2)
timer2.init(period=60*1000*app.cfg.rec, mode=Timer.PERIODIC, callback=record)

gc.enable()
