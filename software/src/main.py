# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2025 Matthias Blankertz <matthias@blankertz.org>

import aiorepl  # type: ignore
import asyncio
from errno import ENOENT
import machine
import micropython
import network
import os
import time
import ubinascii

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


def setup_wifi():
    network.hostname("TonberryPico")
    wlan = network.WLAN(network.WLAN.IF_AP)
    wlan.config(ssid=f"TonberryPicoAP_{machine.unique_id().hex()}", security=wlan.SEC_OPEN)
    wlan.active(True)

    # disable power management
    wlan.config(pm=network.WLAN.PM_NONE)

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
        await asyncio.sleep_ms(500)
        wdt.feed()

DB_PATH = '/sd/tonberry.db'

config = Configuration()


def run():
    asyncio.new_event_loop()
    # Setup LEDs
    np = NeoPixel(hwconfig.LED_DIN, config.get_led_count(), sm=1)

    # Wifi with default config
    setup_wifi()

    # Setup MP3 player
    with SDContext(mosi=hwconfig.SD_DI, miso=hwconfig.SD_DO, sck=hwconfig.SD_SCK, ss=hwconfig.SD_CS,
                   baudrate=hwconfig.SD_CLOCKRATE):
        # Temporary hack: build database from folders if no database exists
        # Can be removed once playlists can be created via API
        try:
            _ = os.stat(DB_PATH)
        except OSError as ex:
            if ex.errno == ENOENT:
                print("No playlist DB found, trying to build DB from tag dirs")
                builddb()

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
                                    leds=lambda _: LedManager(np),
                                    config=lambda _: config)
            the_app = app.PlayerApp(deps)

            start_webserver(config, the_app)
            # Start
            wdt = machine.WDT(timeout=1000)
            asyncio.create_task(aiorepl.task({'timer_manager': TimerManager(),
                                              'app': the_app}))
            asyncio.create_task(wdt_task(wdt))
            asyncio.get_event_loop().run_forever()


def builddb():
    """
    For testing, build a playlist db based on the previous tag directory format.
    Can be removed once uploading files / playlist via the web api is possible.
    """
    try:
        os.unlink(DB_PATH)
    except OSError:
        pass
    with BTreeFileManager(DB_PATH) as db:
        for name, type_, _, _ in os.ilistdir(b'/sd'):
            if type_ != 0x4000:
                continue
            fl = [b'/sd/' + name + b'/' + x for x in os.listdir(b'/sd/' + name) if x.endswith(b'.mp3')]
            db.createPlaylistForTag(name, fl)
    os.sync()


if __name__ == '__main__':
    time.sleep(1)
    if machine.Pin(hwconfig.BUTTONS[0], machine.Pin.IN, machine.Pin.PULL_UP).value() != 0:
        run()
