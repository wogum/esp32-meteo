"""
ESP32 Micropython appication base.
Author WG 2019 The MIT License (MIT)
Usage: 
    import app
"""

# GLOBALS
# const version
VERSION = "ESP-201017"
# echo print for debug
debug = False
# placeholder for readings
vals = [0,0,0,0,0,0] 
devs = ['','','','','','Bat']
units = ['','','','','','Vbat[mV]']
# common config
cfg = None
www = None
# common interfaces
i2c = None
pwm = None

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

# localtime as string with milliseconds
def tm():
    import time
    global cfg
    tz = cfg.tz if cfg is not None else 0
    try:
        ms = int(time.time_ns() // 1000000 % 86400000)
    except:
        ms = int(time.time() * 1000)
    h = (ms // 3600000 + tz) % 24
    m = ms // 60000 % 60
    s = ms // 1000 % 60
    ss = ms % 1000
    return "{}{:02d}:{:02d}:{:02d}.{:03d}{}".format(BLUE, h, m, s, ss, END)

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

# sync time
def ntp(server = None):
    import network
    import time
    import ntptime
    wlan = network.WLAN(network.STA_IF)
    timeout = 5000
    # while not connected
    while wlan.ifconfig()[0] == '0.0.0.0' and timeout > 0:
        time.sleep(0.011)
        timeout -= 11
    # if connected
    if wlan.ifconfig()[0] != '0.0.0.0':
        if server is not None:
            ntptime.host = server
        try:
            ntptime.settime()
            print(tm(), "NTP synchronized")
        except:
            return False
        return True
    return False

# print file content
def cat(fname):
    f = open(fname, 'r')
    for line in f:
        print(line.rstrip('\r').rstrip('\n'))
    f.close()
