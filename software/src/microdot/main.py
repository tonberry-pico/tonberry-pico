import rp2
import network
from microdot import Microdot

rp2.country('DE')

wlan = network.WLAN(network.AP_IF)
wlan.config(ssid='TonberryPico', security=network.WLAN.SEC_OPEN)
wlan.ipconfig(addr4='10.0.0.1')
wlan.active(True)   # loads the firmware
wlan.config(pm=network.WLAN.PM_NONE)

#app = Microdot()
#@app.route('/')
#async def index(request):
#    return "TonberryPico says 'Hello World!'"
#
#app.run()
