import asyncio
import network
import ubinascii
import rp2

from mfrc522 import MFRC522
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


def uid_to_string(uid: list):
    return '0x' + ''.join(f'{i:02x}' for i in uid)



async def get_tag_uid(reader: MFRC522, poll_interval_ms: int = 50) -> list:
    '''
    The maximum measured delay with poll_interval_ms=50 and a reader with tocard_retries=5 is
    15.9 ms:
        delay (min / max / avg) [µs]: (360 / 15945 / 1.892923e-06)

    The maximum measured delay dropped to 11.6 ms by setting tocard_retries=1:
        delay (min / max / avg) [µs]: (368 / 11696 / 6.204211e-06)
    '''
    while True:
        reader.init()

        # For now we omit the tag type
        (stat, _) = reader.request(reader.REQIDL)
        if stat == reader.OK:
            (stat, uid) = reader.SelectTagSN()
            if stat == reader.OK:
                print(f"uid={uid_to_string(uid)}")
                return uid

        await asyncio.sleep_ms(poll_interval_ms)


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


@app.route('/nfc')
async def blafasel(request):
    print("/nfc")

    reader = MFRC522(spi_id=1, sck=10, miso=12, mosi=11, cs=13, rst=9, tocard_retries=10)
    task = asyncio.create_task(get_tag_uid(reader))

    uid = await task

    return f"result={uid_to_string(uid)}"

app.run(port=80)
