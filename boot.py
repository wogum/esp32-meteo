# This file is executed on every boot (including wake-boot from deepsleep)
import esp
import network
import webrepl
esp.osdebug(None)
# wifi connect
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
try:
    # read config
    import config
    import app
    app.cfg = config.CONFIG()
    wlan.config(dhcp_hostname=app.cfg.hostname)
    wlan.connect(app.cfg.ssid, app.cfg.pwd)
except:
    wlan.connect('WG', 'voytek66')
webrepl.start()
