# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2025 Matthias Blankertz <matthias@blankertz.org>

import aiorepl
import asyncio
import machine
import micropython
import time
from machine import Pin
from math import pi, sin, pow

# Own modules
import app
from audiocore import AudioContext
from mfrc522 import MFRC522
from mp3player import MP3Player
from nfc import Nfc
from rp2_neopixel import NeoPixel
from utils import Buttons, SDContext, TimerManager

micropython.alloc_emergency_exception_buf(100)


async def rainbow(np, period=10):
    def gamma(value, X=2.2):
        return min(max(int(brightness * pow(value / 255.0, X) * 255.0 + 0.5), 0), 255)

    brightness = 0.5
    count = 0.0
    leds = len(np)
    while True:
        for i in range(leds):
            ofs = (count + i) % leds
            np[i] = (gamma((sin(ofs / leds * 2 * pi) + 1) * 127),
                     gamma((sin(ofs / leds * 2 * pi + 2/3*pi) + 1) * 127),
                     gamma((sin(ofs / leds * 2 * pi + 4/3*pi) + 1) * 127))
        count += 0.2
        before = time.ticks_ms()
        await np.async_write()
        now = time.ticks_ms()
        if before + 20 > now:
            await asyncio.sleep_ms(20 - (now - before))


# Machine setup

# Set 8 mA drive strength and fast slew rate
machine.mem32[0x4001c004 + 6*4] = 0x67
machine.mem32[0x4001c004 + 7*4] = 0x67
machine.mem32[0x4001c004 + 8*4] = 0x67
# high prio for proc 1
machine.mem32[0x40030000 + 0x00] = 0x10


def run():
    asyncio.new_event_loop()
    # Setup LEDs
    pin = Pin.board.GP16
    np = NeoPixel(pin, 10, sm=1)
    asyncio.create_task(rainbow(np))

    # Setup MP3 player
    with SDContext(mosi=Pin(3), miso=Pin(4), sck=Pin(2), ss=Pin(5), baudrate=15000000), \
         AudioContext(Pin(8), Pin(6)) as audioctx:

        # Setup NFC
        reader = MFRC522(spi_id=1, sck=10, miso=12, mosi=11, cs=13, rst=9, tocard_retries=20)

        # Setup app
        deps = app.Dependencies(mp3player=lambda the_app: MP3Player(audioctx, the_app),
                                nfcreader=lambda the_app: Nfc(reader, the_app),
                                buttons=lambda the_app: Buttons(the_app))
        the_app = app.PlayerApp(deps)

        # Start
        asyncio.create_task(aiorepl.task({'timer_manager': TimerManager(),
                                          'app': the_app}))
        asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    if machine.Pin(17, machine.Pin.IN, machine.Pin.PULL_UP).value() != 0:
        time.sleep(5)
        run()
