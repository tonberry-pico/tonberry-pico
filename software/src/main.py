# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2025 Matthias Blankertz <matthias@blankertz.org>

import aiorepl
import asyncio
import machine
import micropython
import os
import time
from machine import Pin
from math import pi, sin, pow

# Own modules
from app import TimerManager, TagPlaybackManager
from audiocore import AudioContext
from mfrc522 import MFRC522
from mp3player import MP3Player
from nfc import Nfc
from rp2_neopixel import NeoPixel
from rp2_sd import SDCard

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


class SDContext:
    def __init__(self, mosi, miso, sck, ss, baudrate):
        self.mosi = mosi
        self.miso = miso
        self.sck = sck
        self.ss = ss
        self.baudrate = baudrate

    def __enter__(self):
        self.sdcard = SDCard(self.mosi, self.miso, self.sck, self.ss, self.baudrate)
        try:
            os.mount(self.sdcard, '/sd')
        except Exception:
            self.sdcard.deinit()
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            os.umount('/sd')
        finally:
            self.sdcard.deinit()


def run():
    asyncio.new_event_loop()
    # Setup LEDs
    pin = Pin.board.GP16
    np = NeoPixel(pin, 10, sm=1)
    asyncio.create_task(rainbow(np))

    # Setup MP3 player
    with SDContext(mosi=Pin(3), miso=Pin(4), sck=Pin(2), ss=Pin(5), baudrate=15000000), \
         AudioContext(Pin(8), Pin(6)) as audioctx:
        player = MP3Player(audioctx)
        player.set_volume(128)
        asyncio.create_task(player.task())

        # Setup app
        timer_manager = TimerManager(True)
        playback_manager = TagPlaybackManager(timer_manager, player)

        # Setup NFC
        reader = MFRC522(spi_id=1, sck=10, miso=12, mosi=11, cs=13, rst=9, tocard_retries=20)
        nfc = Nfc(reader, playback_manager.onTagChange)

        # Start
        asyncio.create_task(aiorepl.task({'player': player, 'timer_manager': timer_manager,
                                          'playback_manager': playback_manager, 'nfc': nfc}))
        asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    run()
