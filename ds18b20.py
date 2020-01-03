"""
Author WG 2019
ESP32 Micropython module for the DS18B20 sensor.
The MIT License (MIT)
Usage: 
    import ds18b20
    ds = ds18b20.DS18B20(16)
    temp = ds.read()
"""

class DS18B20:

    def __init__(self, pin = None):
        from machine import Pin
        from onewire import OneWire
        if pin is None:
            raise ValueError("Pin number is required")
        self.pin = pin
        self.ow = OneWire(Pin(self.pin))
        addrs = self.ow.scan()
        if not addrs:
            raise ValueError("DS18B20 not connected")
        self.addr = addrs[0]
        self.T = None
    
    def read(self):
        import time
        self.ow.reset()
        self.ow.writebyte(0xCC) # skip ROM
        self.ow.writebyte(0x44) # start conversion
        time.sleep_ms(750)
        self.ow.reset()
        self.ow.writebyte(0xCC) # skip ROM
        self.ow.writebyte(0xBE) # read scrachpad
        buf = bytearray(9)
        self.ow.readinto(buf)
        if self.ow.crc8(buf):
            raise ValueError("DS18B20 CRC error")
        temp = buf[1] << 8 | buf[0]
        if temp > 32767:
            temp = temp - 65536
        temp = temp / 16
        if temp != 85:    
            self.T = temp 
        else:
            self.T = 0
        return self.T

    @property
    def address(self):
        a = self.addr
        return "{:02x}-{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}".format(a[0], a[6], a[5], a[4], a[3], a[2], a[1])

    @property
    def temperature(self):
        if self.T is None:
            self.read()
        return self.T
