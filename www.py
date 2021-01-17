"""
ESP32 Micropython www micro server.
Author WG 2019 The MIT License (MIT)
Version 20201119
Usage: 
    import www
    srv = www.WWW(True)
"""

class WWW:

    def __init__(self, start = False):
        self.extparse = None
        self.exthandle = None
        if start:
            try:
                import _thread
                _thread.start_new_thread(self.server, ())
            except Exception as e:
                import app
                print(app.tm(), app.RED, "WWW thread creating error", app.END, repr(e))

    # handle client connection
    def handle(self, cli):
        import os
        import json
        import gc
        import app
        gc.collect()
        request = cli.recv(1300)
        request = request.decode().split(" ")[1].split(" ")[0]
        if app.debug: print(app.tm(), "WWW client request", request)
        filename = request.split('/')[1].split(' ')[0].split('?')[0]
        head = "HTTP/1.0 200 OK\r\n"
        # file from local storage
        if filename == "favicon.ico":
            filename = "favicon.png"
        ls = os.listdir()
        if filename in ls:
            if '.png' in filename:
                head += "Content-Type: image/png"
            elif '.html' in filename:
                head += "Content-Type: text/html"
            elif '.css' in filename:
                head += "Content-Type: text/css"
            elif '.js' in filename:
                head += "Content-Type: application/javascript"
            else:
                head += "Content-Type: text/plain"
            if app.debug: print(app.tm(), "WWW file", filename)
            file = open(filename, "r")
            res = file.read()
            file.close()
        # special resorces
        else:
            head += "Content-Type: application/json\r\nAccess-Control-Allow-Origin: *"
            # file list
            if "/files" in request:
                res = []
                ls = os.listdir()
                for f in ls:
                    s = os.stat(f)
                    res.append([f, s[6]])
                res = json.dumps(res)
            elif "/mem" in request:
                res = self.message(True)
            elif self.exthandle is not None:
                res = self.exthandle(request)
            else:
                res = None
            # readings
            if res is None:
                res = self.message(False)
        head += '\r\n\r\n'   
        cli.sendall(head)
        cli.sendall(res)
        if app.debug: print(app.tm(), "WWW response sent")
        head = None
        res = None
        if "?" in request:
            par = request.split("?")[1].split(" ")[0]
            self.parseresp(par)
        request = None
        par = None

    # HTTP server instance
    def server(self):
        import socket
        import app
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", 80))
            sock.listen(5)
            print(app.tm(), "WWW server start listening")
            while True:
                try:
                    cli, cliaddr = sock.accept()
                    if app.debug: print(app.tm(), "WWW client connected", cliaddr)
                    self.handle(cli)
                except Exception as e:
                    print(app.tm(), app.RED, "WWW ERROR", app.END, repr(e))
                finally:
                    cli.close()
        except Exception as e:
            return
        finally:
            sock.close()
            print(app.tm(), "WWW server stoped")

    # converts values to dict object with optional history
    def message(self, history = False):
        import machine
        import network
        import json
        import ubinascii
        import app
        msg = {}
        msg['node'] = app.cfg.node
        msg['utc'] = "{}T{}".format(app.date(), app.time())
        msg['val'] = app.vals 
        msg['dev'] = app.devs
        msg['label'] = app.units
        msg['ver'] = app.VERSION
        msg['mac'] = ubinascii.hexlify(network.WLAN(network.STA_IF).config('mac'), ':').decode()
        msg['ip'] = network.WLAN(network.STA_IF).ifconfig()[0]
        # every hour add config and history
        if history:
            f = open('config', 'r')
            msg['cfg'] = json.loads(f.read())
            f.close()
            import os
            osv = os.uname()
            msg['os'] = "{}_{}".format(osv[0], osv[3]).replace(" ", "_")
            if osv[0] == 'esp32':
                try:
                    msg['mem'] = ubinascii.b2a_base64(machine.RTC().memory()).rstrip().decode()
                except:
                    pass
        return json.dumps(msg).replace(' ', '')
    
    # send reading and optionaly history and configuration to http server as json
    def httpsend(self, history = False, msg = None, url = None):
        """HTTP send recorded data to URL"""
        import urequests
        import app
        import gc
        if url is None:
            url = app.cfg.url
        if not "http" in url:
            return False
        if msg is None:
            msg = self.message(history)
        res = False
        try:
            gc.collect()
            print(app.tm(), "HTTP sending")
            r = urequests.post(url, data = msg, headers = { "Content-type" : "application/json" })
            if r.status_code == 200:
                if app.debug: print(app.tm(), "HTTP sent", r.status_code, r.text)
                res = True
                if "?" in r.text:
                    self.parseresp(r.text.split("?")[1])
            if not res:
                print(app.tm(), app.RED, "HTTP ERROR in send", r.status_code, app.END, r.reason)
        except Exception as e:
                print(app.tm(), app.RED, "HTTP send exception: ", app.END, repr(e))
        return res    

    # parse url
    def parseurl(self, req):
        """splits url request parameters into dictionary"""
        parameters = {}
        values = req.split('&')
        try:
            for element in values:
                pair = element.split('=')
                parameters[pair[0]] = pair[1]
        except:
            pass
        return parameters

    # parse response
    def parseresp(self, resp):
        """parses config related parameters from url request"""
        import json
        import machine
        import ubinascii
        import os
        import app
        if app.debug: print("URL Request", resp)
        par = self.parseurl(resp)
        try:
            # runtime operations
            if self.extparse is not None:
                self.extparse(par)
            # config oprerations
            if app.cfg.parse(par):
                print(app.tm(), "URL PARSE new config", app.cfg.read())
                if "http://" in app.cfg.url:
                    self.httpsend(True)
                #elif "mqtt://" in app.cfg.url:
                #    self.mqttsend(True)
                else:
                    pass
            # file operations
            if "frm" in par:
                val = str(par['frm'])
                ls = os.listdir()
                if "tmp.tmp" in ls:
                    os.remove("tmp.tmp")
                if val in ls:
                    os.remove(val)
            elif "fap" in par:
                val = str(par['fap']).replace('-','+').replace('_','/').replace('.','=')
                while (len(val) % 4) != 0:
                    val += '='
                ls = ubinascii.a2b_base64(val).decode()
                f = open("tmp.tmp", "a")
                f.write(ls)
                f.close()
            elif "fmv" in par:
                val = str(par['fmv'])
                ls = os.listdir()
                if "tmp.tmp" in ls:
                    if val in ls:
                        os.remove(val)
                    os.rename("tmp.tmp", val)
            elif "fdo" in par:
                val = str(par['fdo'])
                if ".py" in val:
                    __import__(val.split('.')[0])
            # remove from RTC memory by restart
            elif "rm" in par:
                val = int(par["rm"])
                if val > 0:
                    print(app.tm(), app.RED, "RESET REQUEST", app.END)
                    machine.reset()
            # restart by deepsleep operation
            elif "rst" in par:
                val = int(par['rst'])
                if val > 0:
                    print(app.tm(), app.RED, "RESTART REQUEST", app.END)
                    machine.deepsleep(10)
        except:
            pass
