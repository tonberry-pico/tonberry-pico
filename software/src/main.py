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


class Buttons:
    def __init__(self, player, pin_volup=17, pin_voldown=19, pin_next=18):
        self._VOLUP = micropython.const(1)
        self._VOLDOWN = micropython.const(2)
        self._NEXT = micropython.const(3)
        self.player = player
        self.buttons = {machine.Pin(pin_volup, machine.Pin.IN, machine.Pin.PULL_UP): self._VOLUP,
                        machine.Pin(pin_voldown, machine.Pin.IN, machine.Pin.PULL_UP): self._VOLDOWN,
                        machine.Pin(pin_next, machine.Pin.IN, machine.Pin.PULL_UP): self._NEXT}
        self.int_flag = asyncio.ThreadSafeFlag()
        self.pressed = []
        self.last = {}
        for button in self.buttons.keys():
            button.irq(handler=self._interrupt, trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING)

    def _interrupt(self, button):
        keycode = self.buttons[button]
        last = self.last.get(keycode, 0)
        now = time.ticks_ms()
        self.last[keycode] = now
        if now - last < 10:
            # debounce, discard
            return
        if button.value() == 0:
            # print(f'B{keycode} {now}')
            self.pressed.append(keycode)
            self.int_flag.set()

    async def task(self):
        while True:
            await self.int_flag.wait()
            while len(self.pressed) > 0:
                what = self.pressed.pop()
                if what == self._VOLUP:
                    self.player.set_volume(min(255, self.player.get_volume()+1))
                elif what == self._VOLDOWN:
                    self.player.set_volume(max(0, self.player.get_volume()-1))
                elif what == self._NEXT:
                    self.player.play_next()


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
        player.set_volume(32)
        asyncio.create_task(player.task())

        buttons = Buttons(player)
        asyncio.create_task(buttons.task())

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
