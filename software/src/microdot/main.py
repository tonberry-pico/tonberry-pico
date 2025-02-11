import rp2
import network
import ubinascii
from microdot import Microdot

rp2.country('DE')

wlan = network.WLAN(network.AP_IF)
wlan.config(ssid='TonberryPico', security=network.WLAN.SEC_OPEN)
# Important: we cannot change the ip in station mode, otherwise dhcp won't work!
# wlan.ipconfig(addr4='10.0.0.1')
wlan.active(True)   # loads the firmware
while wlan.active() is False:
    pass
wlan.config(pm=network.WLAN.PM_NONE)

mac = ubinascii.hexlify(network.WLAN().config('mac'), ':').decode()
print(f"     mac: {mac}")
print(f" channel: {wlan.config('channel')}")
print(f"   essid: {wlan.config('essid')}")
print(f" txpower: {wlan.config('txpower')}")
print(f"ifconfig: {wlan.ifconfig()}")

app = Microdot()


@app.route('/')
async def index(request):
    print("wohoo, a guest :)")
    print(f"  app: {request.app}")
    print(f"  client: {request.client_addr}")
    print(f"  method: {request.method}")
    print(f"  url: {request.url}")
    print(f"  headers: {request.headers}")
    print(f"  cookies: {request.cookies}")
    return "TonberryPico says 'Hello World!'"

app.run(port=80)
