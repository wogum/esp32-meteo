"""
Author WG 2019
ESP32 Micropython module for the Bosch BMP180 sensor.
https://ae-bst.resource.bosch.com/media/_tech/media/datasheets/BST-BMP180-DS000.pdf
The MIT License (MIT)
Usage: 
    import bmp180
    from machine import I2C, Pin
    i2c = I2C(scl=Pin(22), sda=Pin(21), freq=100000)
    bmp180 = bmp180.BMP180(i2c)
    temp, press = bmp180.read()
"""

class BMP180:

    # BMP180 fixed i2c address
    BMP180_I2CADDR  = 0x77
    # BMP180 chip id
    BMP180_MAGIC    = 0x55
    # BMP180 registers
    BMP180_CHIPID   = 0xD0
    BMP180_CONTROL  = 0xF4
    BMP180_MSB      = 0xF6

    # creator
    def __init__(self, i2c = None):
        from struct import unpack 
        if i2c is None:
            raise ValueError("I2C object is required.")
        self.i2c = i2c
        chipid = self.i2c.readfrom_mem(self.BMP180_I2CADDR, self.BMP180_CHIPID, 1)[0]
        if chipid != 0x55:
            raise ValueError("BMP180 device not present")
        # set default oversample settings
        self.oss = 3
        # last reading
        self.T = None
        self.P = None
        # read calibration data
        self.AC1, self.AC2, self.AC3, self.AC4, self.AC5, self.AC6, \
            self.B1, self.B2, self.MB, self.MC, self.MD = \
            unpack('>hhhHHHhhhhh', self.i2c.readfrom_mem(self.BMP180_I2CADDR, 0xAA, 22)) 

    # read temperatrure in dec C and pressure in hPa
    def read(self, result = None):
        from struct import unpack 
        import time
        # read raw values at 0xF6
        self.i2c.writeto_mem(self.BMP180_I2CADDR, self.BMP180_CONTROL, bytearray([0x2E]))
        time.sleep_ms(5) # >4.5ms for temperature reading
        UT = unpack('>H', self.i2c.readfrom_mem(self.BMP180_I2CADDR, self.BMP180_MSB, 2))[0]
        self.i2c.writeto_mem(self.BMP180_I2CADDR, self.BMP180_CONTROL, bytearray([0x34 + (self.oss << 6)]))
        time.sleep_ms(2 + (3 << self.oss)) # 5, 8, 14, 26ms for oss 0, 1, 2, 3 - pressure reading
        MSB, LSB, XLSB = unpack('BBB', self.i2c.readfrom_mem(self.BMP180_I2CADDR, self.BMP180_MSB, 3))
        UP = ((MSB << 16) + (LSB << 8) + XLSB) >> (8 - self.oss) #raw pressure
        # temperature calculation T deg C
        X1 = ((UT - self.AC6) * self.AC5) >> 15
        X2 = (self.MC << 11) // (X1 + self.MD)
        B5 = X1 + X2
        self.T = (((X1 + X2) + 8) >> 4) / 10
        # pressure calculation P hPa
        B6 = B5 - 4000
        X1 = (self.B2 * ((B6 * B6) >> 12)) >> 11
        X2 = (self.AC2 * B6) >> 11
        X3 = X1 + X2
        B3 = (((int(self.AC1) * 4 + X3) << self.oss) + 2) >> 2
        X1 = (self.AC3 * B6) >> 13
        X2 = (self.B1 * ((B6 * B6) >> 12)) >> 16
        X3 = ((X1 + X2) + 2) >> 2
        B4 = (self.AC4 * (X3 + 32768)) >> 15
        B7 = (UP - B3) * (50000 >> self.oss)
        if B7 < 0x80000000:
            if B4 != 0:
                pressure = (B7 << 1) // B4
            else:
                raise ValueError("BMP180 invalid data")
        else:
            if B4 != 0:
                pressure = (B7 // B4) << 1
            else:
                raise ValueError("BMP180 invalid data")
        X1 = (pressure >> 8) * (pressure >> 8)
        X1 = (X1 * 3038) >> 16
        X2 = (-7357 * pressure) >> 16
        pressure = pressure + ((X1 + X2 + 3791) >> 4)
        self.P = pressure / 100
        # result
        if result is not None:
            result[0] = self.T
            result[1] = self.P
            return result
        else:
            return (self.T, self.P)
