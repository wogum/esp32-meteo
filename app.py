"""
ESP32 Micropython appication base.
Author WG 2019 The MIT License (MIT)
Usage: 
    import app
"""

# GLOBALS
# const version
VERSION = "ESP-200105"
# echo print for debug
debug = False
# placeholder for readings
#vals = [ 0->v, i, p, c, e, 5->bat, ts, d ]
vals = [0,0,0,0,0,0] 
devs = ['','','','','','Bat']
units = ['','','','','','Vbat[mV]']
# common config
cfg = None
www = None
# common interfaces
adc = None
i2c = None
#uart = None
#ina = None
#oled = None

# const
END             = "\033[0m"
BOLD            = "\033[1m"
BLINK           = "\033[5m"
BLACK           = "\033[30m"
RED             = "\033[31m"
GREEN           = "\033[32m"
BROWN           = "\033[33m"
BLUE            = "\033[34m"
MAGENTA         = "\033[35m"
CYAN            = "\033[36m"
LIGHTGRAY       = "\033[37m"
DARKGRAY        = "\033[90m"
LIGHTRED        = "\033[91m"
LIGHTGREEN      = "\033[92m"
YELLOW          = "\033[93m"
LIGHTBLUE       = "\033[94m"
LIGHTMAGENTA    = "\033[95m"
LIGHTCYAN       = "\033[96m"
WHITE           = "\033[97m"


# time as string
def time(secs = None):
    import time
    tm = time.localtime(secs)
    return "{:02d}:{:02d}:{:02d}".format(tm[3], tm[4], tm[5])

# date as string
def date(secs = None):
    import time
    tm = time.localtime(secs)
    return "{:04d}-{:02d}-{:02d}".format(tm[0], tm[1], tm[2])

# time as string with 0.1 seconds
def tm():
    import time
    global cfg
    if cfg is not None:
        secs = time.time() + 3600 * cfg.tz
    else:
        secs = None
    tm = time.localtime(secs)
    ms = (time.ticks_ms() % 10000) 
    return "{}{:02d}:{:02d}:{:02d}({:04d}){}".format(BLUE, tm[3], tm[4], tm[5], ms, END)

# internal battery voltage for Lolin D32
def bat():
    from machine import ADC, Pin
    import os
    if os.uname()[0] == "esp8266":
        bat = ADC(0)
    else:
        bat = ADC(Pin(35))
        bat.atten(ADC.ATTN_11DB)
    vl = bat.read()
    mx = vl
    mn = vl
    for _ in range(11):
        v = bat.read()
        vl += v
        if v > mx:
            mx = v
        if v < mn:
            mn = v
    vl = vl - mx - mn
    if os.uname()[0] == "esp8266":
        vl *= 0.573
    else:
        vl *= 0.176
    return int(round(vl))

# start led blinking
def led(pin = 2, duty = 3, freq = 2):
    if pin == 0:
        return None
    from machine import PWM, Pin
    pwm2 = PWM(Pin(abs(pin)))
    pwm2.freq(freq)
    if pin < 0:
        duty = 1023 - duty
    pwm2.duty(duty)
    return pwm2

# restart by deepsleep
def rst(sek = 1):
    import machine
    machine.deepsleep(sek * 1000)

def ntp(server = None):
    import network
    import time
    import ntptime
    wlan = network.WLAN(network.STA_IF)
    timeout = 5000
    while not wlan.isconnected() and timeout > 0:
        time.sleep(0.011)
        timeout -= 11
    if wlan.isconnected():
        if server is not None:
            ntptime.host = server
        try:
            ntptime.settime()
            print(tm(), "NTP synchronized")
            return True
        except:
            pass
    return False

# print file content
def cat(fname):
    f = open(fname, 'r')
    for line in f:
        print(line.rstrip('\r').rstrip('\n'))
    f.close()
