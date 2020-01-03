
class MEM:

    def __init__(self):
        pass

    # float32 (s+e+m)(1+8+23bits) -> float16 (1+5+10bits)(0.004..16773119)
    def f2b(self, x):
        from struct import pack, unpack
        if x == 0:
            return 0
        l = unpack('>L', pack('>f', float(x)))[0]
        s = l >> 31
        e = ((l >> 23) & 0x00FF) - 127
        m = (l >> 13) & 0x03FF
        if e > 23:
            e = 23
            m = 0x03FF
        elif e < -8:
            return 0
        e += 8
        y = (s << 15) | (e << 10) | m 
        return y

    # float16 (s+e+m)(1+6+9bits) -> float32 (1+8+23bits)
    def b2f(self, x):
        from struct import pack, unpack
        x = int(x) & 0xFFFF
        if x == 0:
            return 0
        s = x >> 15
        e = ((x >> 10) & 0x001F) - 8
        e = e + 127
        m = x & 0x03FF
        l = (s << 31) | (e << 23) | (m << 13) | 0x07FF
        y = unpack('>f', pack('>L', l))[0]
        return y

    # converts values to 16 bytes string
    def mem16(self):
        import time
        from struct import pack
        import app
        tim = int(time.time()) + 946684800
        rec = pack('>L', tim)
        for i in range(6):
            try:
                v = float(app.vals[i])
            except:
                v = 0
            rec += pack('>H', self.f2b(v))
        return rec

    # save to RTC memory
    def savemem(self):
        """Save last 2K/16B readings to RTC memory"""
        import machine
        import time
        import app
        from struct import pack
        if time.time() < 600000000:
            return
        rec = self.mem16()
        mem = machine.RTC().memory()
        mem = mem[-(2048-16):] + rec
        machine.RTC().memory(mem)
        return len(mem)

    # load from RTC memory
    def loadmem(self):
        """Load last 2K/16B readings from RTC memory"""
        import machine
        import time
        from struct import unpack
        mem = machine.RTC().memory()
        while len(mem) >= 16:
            v = unpack('>LHHHHHH', mem[0:16])
            t = [v[1], v[2], v[3], v[4], v[5], v[6]]
            for i in range(6):
                t[i] = self.b2f(t[i])
            tm = time.localtime(v[0] - 946684800)
            s = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*tm) \
                + " [{}, {}, {}, {}, {}, {}]".format(*t)
            print(s)
            mem = mem[16:]
