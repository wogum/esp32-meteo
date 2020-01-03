"""
Author WG 2019
ESP32 Micropython module for the Maxim MAX44009 sensor.
https://datasheets.maximintegrated.com/en/ds/MAX44009.pdf
The MIT License (MIT)
Usage: 
    import max44009
    from machine import I2C, Pin
    i2c = I2C(scl=Pin(22), sda=Pin(21), freq=100000)
    max44009 = max44009.MAX44009(i2c)
    lux = max44009.read()
"""

class MAX44009:
    
    # MAX44009 default i2c address.
    MAX_I2CADDR         = 0x4A
    MAX_CONFIG          = 0x02
    MAX_LUX_HIGH        = 0x03
    MAX_LUX_LOW         = 0x04

    def __init__(self, i2c = None):

        if i2c is None:
            raise ValueError("I2C object is required.")
        self.i2c = i2c
        # i2c address autodetection
        s = self.i2c.scan()
        if self.MAX_I2CADDR in s:
            self.i2caddr = self.MAX_I2CADDR
        elif self.MAX_I2CADDR + 1 in s:
            self.i2caddr = self.MAX_I2CADDR + 1
        else:
            raise ValueError("MAX44009 Device not present")

        # configuration default auto mode with 100ms integration, 
        self.i2c.writeto_mem(self.i2caddr, self.MAX_CONFIG, bytearray([0x03]))

        # last readings
        self.lux = None

    def read(self):
        # MAX44009 does not have autoincremet registers address so one have to read byte by byte without stop between
        msb = bytearray(1)
        lsb = bytearray(1)
        self.i2c.writeto(self.MAX_I2CADDR, bytearray([self.MAX_LUX_HIGH]), False)
        self.i2c.readfrom_into(self.MAX_I2CADDR, msb, False)
        self.i2c.writeto(self.MAX_I2CADDR, bytearray([self.MAX_LUX_LOW]), False)
        self.i2c.readfrom_into(self.MAX_I2CADDR, lsb, True)
        msb = msb[0]
        lsb = lsb[0]
        exponent = msb >> 4
        mantissa = ((msb & 0x0F) << 4) | (lsb & 0x0F)
        self.lux = int((1 << exponent) * mantissa * 0.045)
        return self.lux

    @property
    def luminosity(self):
        if self.lux is None:
            self.read()
        return self.lux

    @property
    def UV(self):
        return 0

    @property
    def IR(self):
        return 0
