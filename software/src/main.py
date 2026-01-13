# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2025 Matthias Blankertz <matthias@blankertz.org>

import aiorepl  # type: ignore
import asyncio
import machine
import micropython
import network
import time
import ubinascii
import sys

# Own modules
import app
from audiocore import AudioContext
import frozen_frontend  # noqa: F401
from mfrc522 import MFRC522
from mp3player import MP3Player
from nfc import Nfc
from rp2_neopixel import NeoPixel
from utils import BTreeFileManager, Buttons, SDContext, TimerManager, LedManager, Configuration
from webserver import start_webserver

try:
    import hwconfig
except ImportError:
    print("Fatal: No hwconfig.py found")
    raise

micropython.alloc_emergency_exception_buf(100)

# Machine setup
hwconfig.board_init()

# high prio for proc 1
machine.mem32[0x40030000 + 0x00] = 0x10


def setup_wifi(ssid='', passphrase='', security=network.WLAN.SEC_WPA_WPA2):
    network.hostname("TonberryPico")
    if ssid is None or ssid == '':
        apname = f"TonberryPicoAP_{machine.unique_id().hex()}"
        print(f"Create AP {apname}")
        wlan = network.WLAN(network.WLAN.IF_AP)
        wlan.config(ssid=apname, password=passphrase if passphrase is not None else '', security=security)
        wlan.active(True)
    else:
        print(f"Connect to SSID {ssid} with passphrase {passphrase}...")
        wlan = network.WLAN()
        wlan.active(True)
        wlan.connect(ssid, passphrase if passphrase is not None else '', security=security)

    # configure power management
    wlan.config(pm=network.WLAN.PM_PERFORMANCE)

    mac = ubinascii.hexlify(network.WLAN().config('mac'), ':').decode()
    print(f"     mac: {mac}")
    print(f" channel: {wlan.config('channel')}")
    print(f"   essid: {wlan.config('essid')}")
    print(f" txpower: {wlan.config('txpower')}")
    print(f"ifconfig: {wlan.ifconfig()}")


async def wdt_task(wdt):
    # TODO: more checking of app health
    # Right now this only protects against the asyncio executor crashing completely
    while True:
        await asyncio.sleep_ms(100)
        wdt.feed()

DB_PATH = '/sd/tonberry.db'

config = Configuration()

# Setup LEDs
np = NeoPixel(hwconfig.LED_DIN, config.get_led_count(), sm=1)
led_max = config.get_led_max()
np.fill((led_max, led_max, 0))
np.write()


def run():
    asyncio.new_event_loop()

    if machine.Pin(hwconfig.BUTTONS[1], machine.Pin.IN, machine.Pin.PULL_UP).value() == 0:
        np.fill((0, 0, led_max))
        np.write()
        # Force default access point
        setup_wifi('', '', network.WLAN.SEC_OPEN)
    else:
        secstring = config.get_wifi_security()
        security = network.WLAN.SEC_WPA_WPA2
        if secstring == 'open':
            security = network.WLAN.SEC_OPEN
        elif secstring == 'wpa_wpa2':
            security = network.WLAN.SEC_WPA_WPA2
        elif secstring == 'wpa3':
            security = network.WLAN.SEC_WPA3
        elif secstring == 'wpa2_wpa3':
            security = network.WLAN.SEC_WPA2_WPA3
        setup_wifi(config.get_wifi_ssid(), config.get_wifi_passphrase(), security)

    # Setup MP3 player
    with SDContext(mosi=hwconfig.SD_DI, miso=hwconfig.SD_DO, sck=hwconfig.SD_SCK, ss=hwconfig.SD_CS,
                   baudrate=hwconfig.SD_CLOCKRATE):
        with BTreeFileManager(DB_PATH) as playlistdb, \
             AudioContext(hwconfig.I2S_DIN, hwconfig.I2S_DCLK, hwconfig.I2S_LRCLK) as audioctx:

            # Setup NFC
            reader = MFRC522(spi_id=hwconfig.RC522_SPIID, sck=hwconfig.RC522_SCK, miso=hwconfig.RC522_MISO,
                             mosi=hwconfig.RC522_MOSI, cs=hwconfig.RC522_SS, rst=hwconfig.RC522_RST, tocard_retries=20)

            # Setup app
            deps = app.Dependencies(mp3player=lambda the_app: MP3Player(audioctx, the_app),
                                    nfcreader=lambda the_app: Nfc(reader, the_app),
                                    buttons=lambda the_app: Buttons(the_app, config, hwconfig),
                                    playlistdb=lambda _: playlistdb,
                                    hwconfig=lambda _: hwconfig,
                                    leds=lambda _: LedManager(np, config),
                                    config=lambda _: config)
            the_app = app.PlayerApp(deps)

            start_webserver(config, the_app)
            # Start
            wdt = machine.WDT(timeout=2000)
            asyncio.create_task(aiorepl.task({'timer_manager': TimerManager(),
                                              'app': the_app}))
            asyncio.create_task(wdt_task(wdt))
            asyncio.get_event_loop().run_forever()


def error_blink():
    while True:
        if machine.Pin(hwconfig.BUTTONS[0], machine.Pin.IN, machine.Pin.PULL_UP).value() == 0:
            machine.reset()
        np.fill((led_max, 0, 0))
        np.write()
        time.sleep_ms(500)
        np.fill((0, 0, 0))
        np.write()
        time.sleep_ms(500)


if __name__ == '__main__':
    time.sleep(1)
    if machine.Pin(hwconfig.BUTTONS[0], machine.Pin.IN, machine.Pin.PULL_UP).value() != 0:
        try:
            run()
        except Exception as ex:
            sys.print_exception(ex)
            error_blink()
    else:
        np.fill((led_max, 0, 0))
        np.write()
