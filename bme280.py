"""
Author WG 2019
ESP32 Micropython module for the Bosch BME280 enviroment TPH sensor.
https://ae-bst.resource.bosch.com/media/_tech/media/datasheets/BST-BME280-DS002.pdf
The MIT License (MIT)
Usage: 
    import bme280
    from machine import I2C, Pin
    i2c = I2C(scl=Pin(22), sda=Pin(21), freq=100000)
    bme280 = bme280.BME280(i2c)
    temp, press, humi = bme280.read()
"""

class BME280:
    
    # BME280 default i2c address.
    BME280_I2CADDR      = 0x76
    # BME280 chip id
    BME280_MAGIC        = 0x60
    # BMP280 chip id
    BMP280_MAGIC        = 0x58
    # BME280 registers
    BME280_CHIPID       = 0xD0
    BME280_CONTROL_HUM  = 0xF2
    BME280_CONTROL      = 0xF4
    BME280_CONFIG       = 0xF5

    def __init__(self, i2c = None):
        from struct import unpack
        if i2c is None:
            raise ValueError("I2C object is required.")
        self.i2c = i2c
        # i2c address autodetection
        s = self.i2c.scan()
        if self.BME280_I2CADDR in s:
            self.i2caddr = self.BME280_I2CADDR
        elif self.BME280_I2CADDR + 1 in s:
            self.i2caddr = self.BME280_I2CADDR + 1
        else:
            raise ValueError("BME280 Device not present")
        # chip model check
        self.chipid = self.i2c.readfrom_mem(self.i2caddr, self.BME280_CHIPID, 1)[0]
        if self.chipid not in [self.BMP280_MAGIC, self.BME280_MAGIC]:
            raise ValueError("BME280/BMP280 Device not present")
        # set oversample setting 1..5
        self.osrs = 3
        # calibration data at 0x88
        self.T1, self.T2, self.T3, \
            self.P1, self.P2, self.P3, self.P4, self.P5, \
            self.P6, self.P7, self.P8, self.P9 = \
            unpack("<HhhHhhhhhhhh", self.i2c.readfrom_mem(self.i2caddr, 0x88, 24))
        if self.chipid == self.BME280_MAGIC:
            self.H1 = self.i2c.readfrom_mem(self.i2caddr, 0xA1, 1)[0]
            self.H2, self.H3, E4, E5, E6, self.H6 = unpack("<hBbBbb", self.i2c.readfrom_mem(self.i2caddr, 0xE1, 7))
            self.H4 = (E4 << 4) | (E5 & 0x0F)
            self.H5 = (E6 << 4) | (E5 >> 4)
        # configuration 1000ms, no filter, i2c mode
        self.i2c.writeto_mem(self.i2caddr, self.BME280_CONFIG, b'\xA0')
        # last readings
        self.t_fine = 0
        self.T = None
        self.P = None
        self.H = None

    def read(self, result = None):
        import time
        from struct import unpack
        # read uncompensated raw data
        # control - forced mode with osrs oversampling
        if self.chipid == self.BME280_MAGIC:
            self.i2c.writeto_mem(self.i2caddr, self.BME280_CONTROL_HUM, bytearray([self.osrs]))
        self.i2c.writeto_mem(self.i2caddr, self.BME280_CONTROL, bytearray([(self.osrs << 5) | (self.osrs << 2) | 1]))
        # measure time sleep
        if self.chipid == self.BME280_MAGIC:
            sleep_time = 1250 + 2300 * (1 << self.osrs) + 2300 * (1 << self.osrs) + 575 + 2300 * (1 << self.osrs) + 575
        else:
            sleep_time = 1800 + 2300 * (1 << self.osrs) + 2300 * (1 << self.osrs)
        time.sleep_us(sleep_time)  
        # read measurement at 0xF7
        adc_press, pxlsb, adc_temp, txlsb, adc_hum = unpack(">HBHBH", self.i2c.readfrom_mem(self.i2caddr, 0xF7, 8))
        adc_press = (adc_press << 4) | (pxlsb >> 4)
        adc_temp = (adc_temp << 4) | (txlsb >> 4)
        # temperature calculation T deg C
        var1 = (((adc_temp >> 3) - (self.T1 << 1)) * self.T2) >> 11
        var2 = (((((adc_temp >> 4) - self.T1) * ((adc_temp >> 4) - self.T1)) >> 12) * self.T3) >> 14
        self.t_fine = var1 + var2
        self.T = ((self.t_fine * 5 + 128) >> 8) / 100
        # pressure calculation P hPa
        var1 = self.t_fine - 128000
        var2 = var1 * var1 * self.P6
        var2 = var2 + ((var1 * self.P5) << 17)
        var2 = var2 + (self.P4 << 35)
        var1 = ((var1 * var1 * self.P3) >> 8) + ((var1 * self.P2) << 12)
        var1 = (((1 << 47) + var1) * self.P1) >> 33
        if var1 == 0:
            self.P = 0
        else:
            p = 1048576 - adc_press
            p = (((p << 31) - var2) * 3125) // var1
            var1 = (self.P9 * (p >> 13) * (p >> 13)) >> 25
            var2 = (self.P8 * p) >> 19
            self.P = (((p + var1 + var2) >> 8) + (self.P7 << 4)) / 25600
        # humidity calculation H %
        if self.chipid == self.BME280_MAGIC:
            h = self.t_fine - 76800
            h = ((((adc_hum << 14) - (self.H4 << 20) - (self.H5 * h)) + 16384) >> 15) * \
                (((((((h * self.H6) >> 10) * (((h * self.H3) >> 11) + 32768)) >> 10) + 2097152) * self.H2 + 8192) >> 14)
            h = h - (((((h >> 15) * (h >> 15)) >> 7) * self.H1) >> 4)
            h = 0 if h < 0 else h
            h = 419430400 if h > 419430400 else h
            self.H = (h >> 12) / 1024
        else:
            self.H = 0
        # result
        if result is not None:
            result[0] = self.T 
            result[1] = self.P
            result[2] = self.H
            return result
        else:
            return (self.T, self.P, self.H)
