"""
ESP32 module based meter
config module - import in every other module
Author WG 2019 MIT licence
"""


class CONFIG:

    def __init__(self, filename = "config"):
        import os
        self.filename = filename
        self.node = self.nodeid()
        self.hostname = "{}-{}".format(os.uname()[1], self.node)
        self.led = 0
        self.cal = [1,1,1,1,1,1]
        self.dt = [0,0,0,0,0,0]
        self.ntp = "pool.ntp.org"
        self.ssid = "internet"
        self.pwd = "internet"
        self.url = ""
        self.rec = 15
        self.slp = 0
        self.tz = 1
        if self.filename in os.listdir():
            self.read()
        else:
            self.write()

    def nodeid(self):
        import machine
        mac = machine.unique_id()
        l = len(mac)
        return (mac[l-2] << 8) | mac[l-1]

    # Saves config in file
    def write(self):
        """writes config to file as json string"""
        import json
        cfg = {}
        cfg['node'] = self.node
        cfg['hostname'] = self.hostname
        cfg['led'] = self.led
        cfg['ntp'] = self.ntp
        cfg['cal'] = self.cal
        cfg['dt'] = self.dt
        cfg['ssid'] = self.ssid
        cfg['pwd'] = self.pwd
        cfg['url'] = self.url
        cfg['rec'] = self.rec
        cfg['slp'] = self.slp
        cfg['tz'] = self.tz
        file = open(self.filename, 'w')
        file.write(json.dumps(cfg).replace(' ', ''))
        file.close()

    # Restores config from file
    def read(self):
        """reads json string of config from file"""
        import json
        import os
        try:
            file = open(self.filename, 'r')
            js = file.readline().rstrip('\n').rstrip('\r').replace(' ', '') 
            file.close()
        except:
            js = '{}'
        cfg = json.loads(js)
        self.led = int(cfg.get('led', self.led))
        self.cal = cfg.get('cal', self.cal)
        self.dt = cfg.get('dt', self.dt)
        self.ntp = cfg.get('ntp', self.ntp)
        self.ssid = cfg.get('ssid', self.ssid)
        self.pwd = cfg.get('pwd', self.pwd)
        self.url = cfg.get('url', self.url)
        self.rec = abs(int(cfg.get('rec', self.rec)))
        self.slp = abs(int(cfg.get('slp', self.slp)))
        self.tz = int(cfg.get('tz', self.tz))
        self.hostname = cfg.get('hostname', self.hostname)
        return js

    # Parse dictionary of parameters from HTTP response
    def parse(self, par):
        import json
        new = False
        try:
            # config oprerations
            if "slp" in par:
                self.slp = abs(int(par['slp']))
                new = True
            if "rec" in par:
                self.rec = abs(int(par['rec']))
                new = True
            if "cal" in par:
                self.cal = json.loads(str(par['cal']).replace(
                    '%5B', '[').replace('%5D', ']').replace('%2C', ','))
                new = True
            if "dt" in par:
                self.cal = json.loads(str(par['dt']).replace(
                    '%5B', '[').replace('%5D', ']').replace('%2C', ','))
                new = True
            if "url" in par:
                self.url = str(par['url']).replace(
                    '%3A', ':').replace('%2F', '/')
                new = True
            if "tz" in par:
                self.tz = int(par['tz'])
                new = True
            if "ntp" in par:
                self.ntp = str(par['ntp'])
                new = True
                import ntptime
                ntptime.host = self.ntp
                ntptime.settime()
            if "ssid" in par and "pwd" in par:
                self.ssid = str(par['ssid'])
                self.pwd = str(par['pwd'])
                new = True
            if "led" in par:
                self.led = int(par["led"])
                new = True
            if "hostname" in par:
                self.hostname = str(par['hostname']).replace(' ', '')
            # save and send changed config
            if new:
                self.write()
            return new
        except:
            return False
