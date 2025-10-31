# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2025 Matthias Blankertz <matthias@blankertz.org>

import aiorepl  # type: ignore
import asyncio
import machine
import micropython
import time
from math import pi, sin, pow

# Own modules
import app
from audiocore import AudioContext
from mfrc522 import MFRC522
from mp3player import MP3Player
from nfc import Nfc
from rp2_neopixel import NeoPixel
from utils import BTreeFileManager, Buttons, SDContext, TimerManager

try:
    import hwconfig
except ImportError:
    print("Fatal: No hwconfig.py found")
    raise

micropython.alloc_emergency_exception_buf(100)

# Machine setup
hwconfig.board_init()


async def rainbow(np, period=10):
    def gamma(value, X=2.2):
        return min(max(int(brightness * pow(value / 255.0, X) * 255.0 + 0.5), 0), 255)

    brightness = 0.05
    count = 0.0
    leds = len(np)
    while True:
        for i in range(leds):
            ofs = (count + i) % leds
            np[i] = (gamma((sin(ofs / leds * 2 * pi) + 1) * 127),
                     gamma((sin(ofs / leds * 2 * pi + 2/3*pi) + 1) * 127),
                     gamma((sin(ofs / leds * 2 * pi + 4/3*pi) + 1) * 127))
        count += 0.02 * leds
        before = time.ticks_ms()
        await np.async_write()
        now = time.ticks_ms()
        if before + 20 > now:
            await asyncio.sleep_ms(20 - (now - before))


# high prio for proc 1
machine.mem32[0x40030000 + 0x00] = 0x10


def run():
    asyncio.new_event_loop()
    # Setup LEDs
    np = NeoPixel(hwconfig.LED_DIN, hwconfig.LED_COUNT, sm=1)
    asyncio.create_task(rainbow(np))

    # Setup MP3 player
    with SDContext(mosi=hwconfig.SD_DI, miso=hwconfig.SD_DO, sck=hwconfig.SD_SCK, ss=hwconfig.SD_CS,
                   baudrate=hwconfig.SD_CLOCKRATE), \
         BTreeFileManager('/sd/tonberry.db') as playlistdb, \
         AudioContext(hwconfig.I2S_DIN, hwconfig.I2S_DCLK, hwconfig.I2S_LRCLK) as audioctx:

        # Setup NFC
        reader = MFRC522(spi_id=hwconfig.RC522_SPIID, sck=hwconfig.RC522_SCK, miso=hwconfig.RC522_MISO,
                         mosi=hwconfig.RC522_MOSI, cs=hwconfig.RC522_SS, rst=hwconfig.RC522_RST, tocard_retries=20)

        # Setup app
        deps = app.Dependencies(mp3player=lambda the_app: MP3Player(audioctx, the_app),
                                nfcreader=lambda the_app: Nfc(reader, the_app),
                                buttons=lambda the_app: Buttons(the_app, pin_volup=hwconfig.BUTTON_VOLUP,
                                                                pin_voldown=hwconfig.BUTTON_VOLDOWN,
                                                                pin_next=hwconfig.BUTTON_NEXT),
                                playlistdb=lambda _: playlistdb)
        the_app = app.PlayerApp(deps)

        # Start
        asyncio.create_task(aiorepl.task({'timer_manager': TimerManager(),
                                          'app': the_app}))
        asyncio.get_event_loop().run_forever()


def builddb():
    """
    For testing, build a playlist db based on the previous tag directory format.
    Can be removed once uploading files / playlist via the web api is possible.
    """
    import os

    os.unlink('/sd/tonberry.db')
    with BTreeFileManager('/sd/tonberry.db') as db:
        for name, type_, _, _ in os.ilistdir(b'/sd'):
            if type_ != 0x4000:
                continue
            fl = [b'/sd/' + name + b'/' + x for x in os.listdir(b'/sd/' + name) if x.endswith(b'.mp3')]
            db.createPlaylistForTag(name, fl)
    os.sync()


if __name__ == '__main__':
    time.sleep(1)
    if machine.Pin(hwconfig.BUTTON_VOLUP, machine.Pin.IN, machine.Pin.PULL_UP).value() != 0:
        run()
