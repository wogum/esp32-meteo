"""
Author WG 2019
ESP32 MicroPython module for the SI1145 light sensor
https://www.silabs.com/documents/public/data-sheets/Si1145-46-47.pdf
The MIT License (MIT)
Usage: 
    import si1145
    from machine import I2C, Pin
    i2c = I2C(scl=Pin(22), sda=Pin(21), freq=100000)
    sens = si1145.SI1145(i2c)
    uv = sens.UV
    ir = sens.IR
    vis = sens.V
"""

# I2C address
SI1145_ADDR = 0x60
# Commands
SI1145_RESET = 0x01
SI1145_PARAM_SET = 0xA0
# Parameters
SI1145_PARAM_CHLIST = 0x01
# Registers
SI1145_REG_INTCFG = 0x03
SI1145_REG_IRQEN = 0x04
SI1145_REG_HWKEY = 0x07
SI1145_REG_IRQMODE1 = 0x05
SI1145_REG_IRQMODE2 = 0x06
SI1145_REG_HWKEY = 0x07
SI1145_REG_MEASRATE0 = 0x08
SI1145_REG_MEASRATE1 = 0x09
SI1145_REG_UCOEFF0 = 0x13
SI1145_REG_UCOEFF1 = 0x14
SI1145_REG_UCOEFF2 = 0x15
SI1145_REG_UCOEFF3 = 0x16
SI1145_REG_PARAMWR = 0x17
SI1145_REG_COMMAND = 0x18
SI1145_REG_IRQSTAT = 0x21
SI1145_REG_PARAMRD = 0x2E

class SI1145:


    def __init__(self, i2c=None):
        import time
        from ustruct import unpack
        if i2c is None:
            raise ValueError('An I2C object is required')
        self.i2c = i2c
        self.i2caddr = SI1145_ADDR
        s = self.i2c.scan()
        if (SI1145_ADDR not in s) or (self.i2c.readfrom_mem(self.i2caddr, 0x00, 1)[0] != 0x45):
            raise ValueError('Si1145 device not present')
        self.reset()
        self.calibration()
        # Undocumented, checked in practice, readinga are available after 960ms, 
        #   needed in battery deep sleep wake up operation
        to = time.ticks_ms() + 2000
        vis = unpack("<H", self.i2c.readfrom_mem(self.i2caddr, 0x22, 2))[0]
        while (time.ticks_ms() < to) and (vis == 0):
            time.sleep_ms(10)
            vis = unpack("<H", self.i2c.readfrom_mem(self.i2caddr, 0x22, 2))[0]
        # Firs reading ready end of init


    def reset(self):
        import time
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_MEASRATE0, b'\x00')
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_MEASRATE1, b'\x00')
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_IRQEN, b'\x00')
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_IRQMODE1, b'\x00')
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_IRQMODE2, b'\x00')
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_INTCFG, b'\x00')
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_IRQSTAT, b'\xFF')
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_COMMAND, bytes([SI1145_RESET]))
        time.sleep_ms(10)
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_HWKEY, b'\x17')
        time.sleep_ms(10)

    def read(self):
        from ustruct import unpack
        vis = unpack("<H", self.i2c.readfrom_mem(self.i2caddr, 0x22, 2))[0]
        vis = (vis - 256) * 14.5 / 0.282    # weak calculation of lux
        if vis < 0: vis = 0
        return int(vis)

    def writeparam(self, parameter, value):
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_PARAMWR, bytes([value]))
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_COMMAND, bytes([parameter | SI1145_PARAM_SET]))
        return self.i2c.readfrom_mem(self.i2caddr, SI1145_REG_PARAMRD, 1)[0]

    def calibration(self):
        # UV coefficients
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_UCOEFF0, b'\x7B')
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_UCOEFF1, b'\x6B')
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_UCOEFF2, b'\x01')
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_UCOEFF3, b'\x00')
        self.writeparam( SI1145_PARAM_CHLIST, 0xB0) # Enable UV, AUX, IR, Vis
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_INTCFG, b'\x01')
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_IRQEN, b'\x01')
        # no LED1
        self.i2c.writeto_mem(self.i2caddr, 0x0F, b'\x03') # LED12  
        self.writeparam(0x07, 0x03) # PS large ir
        self.writeparam(0x02, 0x00) # PS no led
        # PS
        self.writeparam(0x0B, 0)    # adc_gain 1
        self.writeparam(0x0A, 0x70) # counter 511clk
        self.writeparam(0x0C, 0x20 | 0x04)  # hogh range normal proximity
        # IR
        self.writeparam(0x0E, 0x00) # ADC_MUX small IR
        self.writeparam(0x1E, 0)    # adc_gain 1
        self.writeparam(0x1D, 0x70) # counter 511clk
        self.writeparam(0x1F, 0x20) # high range raw
        # Vis
        self.writeparam(0x11, 0)    # adc_gain 1
        self.writeparam(0x10, 0x70) # counter 511clk
        self.writeparam(0x12, 0x20) # high range raw

        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_MEASRATE0, b'\xFF')
        self.i2c.writeto_mem(self.i2caddr, SI1145_REG_COMMAND, b'\x0F')

    @property
    def UV(self):
        from ustruct import unpack
        return unpack("<H", self.i2c.readfrom_mem(self.i2caddr, 0x2C, 2))[0] / 100

    @property
    def IR(self):
        from ustruct import unpack
        ir = unpack("<H", self.i2c.readfrom_mem(self.i2caddr, 0x24, 2))[0]
        ir = (ir - 256) * 14.5 / 2.44   # wek calculation of lux
        if ir < 0: ir = 0
        return int(ir)
