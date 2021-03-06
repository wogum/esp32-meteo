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
  app.vals[5] = int(app.bat() * app.cfg.cal[5] + app.cfg.dt[5])
  # TPH
  if app.bme is not None: 
    try:
      v = app.bme.read()
      if len(v) < 3:
        v.append(0)
    except:
      v = (0, 0, 0)
    for i in range(3):
      app.vals[i] = round(v[i] * app.cfg.cal[i] + app.cfg.dt[i], 1)
  # E, UV
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
  # T2
  if app.ds and app.ds.scan():
    try:
      while app.dsready > time.ticks_ms():
        time.sleep(0.01)
      v = app.ds.read_temp(app.ds.scan()[0])
      if v != 85:
        if app.devs[0] == "DS18B20":
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
  hist = (((time.time() + 60) // 60) % 60) <= 1
  res = app.www.httpsend(hist)
  if res:
    print(app.tm(), app.GREEN, "HTTP sent", app.END)
  if not res or hist:
    if app.mem is not None:
      try:
        v = app.mem.savemem()
        print(app.tm(), "Saved to mem: ", v)
      except:
        pass
  # go deep sleep
  gosleep()
  next = (app.cfg.node & 0x07) + app.cfg.rec * 60 - time.time() % (app.cfg.rec * 60)
  # if not going sleep set next run
  timer2 = Timer(2)
  timer2.init(period=1000*next, mode=Timer.ONE_SHOT, callback=record)
  print(app.tm(), "Wait: ", next)
  """
  # if not going sleep then start BLE advertising
  bleadvert(app.vals[0] if app.units[0].startswith('T') else 0, 
    app.vals[1] if app.units[1].startswith('P') else 0, 
    app.vals[2] if app.units[2].startswith('H') else 0)
  """

# start BLE advertising T, P and H in iNode PTH format
"""
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
"""

# go deep sleep if cfg.slp==1
def gosleep(timer = None):
  from machine import Pin
  import machine
  import time
  import network
  import os
  import app
  if app.cfg.slp > 0:
    # power off
    network.WLAN(network.STA_IF).disconnect()
    network.WLAN(network.STA_IF).active(False)
    if os.uname()[0] == "esp32":
      for pin in (25,26,27,14,12,13,15):
        Pin(pin, Pin.IN, Pin.PULL_HOLD)
    else:
      for pin in (14,4,5,12,13,15):
        Pin(pin, Pin.IN)
    # time to sleep
    next = (app.cfg.node & 0x07) + 30 + app.cfg.rec * 60 - time.time() % (app.cfg.rec * 60)
    print(app.tm(), app.RED, "Deep sleep ", app.END, next)
    next *= 1000
    machine.deepsleep(next)

# start DS18B20 temperature conversion
def dsconvert(timer = None):
  import app
  if app.ds and app.ds.scan():
    app.ds.convert_temp()

# init all 
def startup():
    from machine import Pin, ADC, I2C
    import time
    import os
    import onewire
    import ds18x20
    import app
    import www

    # devices and values
    #app.devs = ["BME280","","","DS18B20","Si1145","Vbat"]
    #app.units = ["T1[C]","P[hPa]","H[%]","T2[C]","I[lx]","Vbat[mV]"]

    # led
    if app.cfg.led != 0:
        app.pwm = app.led(app.cfg.led)
    app.bme = None
    app.lux = None
    app.mem = None
    app.ds = None
    # i2c
    if os.uname()[0] == 'esp8266':
      # i2c pins
      Pin(14, Pin.OUT, Pin.PULL_UP, value=1)
      Pin(4, Pin.IN, Pin.PULL_UP)
      Pin(5, Pin.IN, Pin.PULL_UP)
      app.i2c = I2C(scl=Pin(5), sda=Pin(4), freq=400000)
    else: 
      import mem
      app.mem = mem.MEM()
      # i2c pins
      Pin(26, Pin.OUT, Pin.PULL_DOWN, value=0)
      Pin(25, Pin.OUT, Pin.PULL_UP, value=1)
      Pin(27, Pin.IN, Pin.PULL_UP)
      Pin(14, Pin.IN, Pin.PULL_UP)
      app.i2c = I2C(0, scl=Pin(27), sda=Pin(14), freq=400000)
      Pin(15, Pin.OUT, Pin.PULL_DOWN, value=0)
    # ds18b20 pins
    Pin(15, Pin.OUT, value=0)
    Pin(13, Pin.OUT, Pin.PULL_UP, value=1)
    Pin(12, Pin.IN, Pin.PULL_UP)
    try:
      app.ds = ds18x20.DS18X20(onewire.OneWire(Pin(12)))
      if app.ds.scan():
        app.ds.convert_temp()
        app.dsready = time.ticks_ms() + 750
        app.devs[3] = "DS18B20"
        app.units[3] = "T2[C]"
    except:
      app.ds = None
    #I2C devices
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
    s = app.i2c.scan()
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
    #ds18b20
    if app.devs[0] == "" and app.devs[3] == "DS18B20":
      app.devs[0] = "DS18B20"
      app.units[0] = "T[C]"
      app.devs[3] = ""
      app.units[3] = ""
    # www
    app.www = www.WWW(os.uname()[0] == 'esp32')
    #Vbat
    print(app.tm(), app.VERSION, "Node", app.cfg.node, app.cfg.hostname, "Vbat", app.bat())
    print(app.tm(), app.devs)
    print(app.tm(), app.units)



###############################################################################
# MAIN
###############################################################################

app.VERSION = "METEO-210117"
gc.enable()

# timer1=>gosleep, timer2=>record, timer3=>DS18B20.convert_start
timer1 = Timer(1)
timer1.init(period=12000, mode=Timer.ONE_SHOT, callback=gosleep)
timer2 = Timer(2)
timer3 = Timer(3)

startup()
del startup

gc.collect()
gc.threshold(gc.mem_free()//4 + gc.mem_alloc())

record()

if app.ds and app.ds.scan():
  timer3.init(period=60*1000, mode=Timer.PERIODIC, callback=dsconvert)

#app.www.server()
