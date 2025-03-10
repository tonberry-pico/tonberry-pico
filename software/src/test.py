# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

import aiorepl
import asyncio
import machine
import micropython
import os
import time
from machine import Pin
from math import pi, sin, pow
from micropython import const

# Own modules
from audiocore import Audiocore
from rp2_neopixel import NeoPixel
from rp2_sd import SDCard

micropython.alloc_emergency_exception_buf(100)

leds = const(10)
brightness = 0.5


def gamma(value, X=2.2):
    return min(max(int(brightness * pow(value / 255.0, X) * 255.0 + 0.5), 0), 255)


async def rainbow(np, period=10):
    count = 0.0
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


async def play_mp3(audiocore, mp3file):
    _, avail, _ = audioctx.put(b'')
    known_underruns = 0
    while True:
        data = mp3file.read(avail)
        if avail > 0 and len(data) == 0:
            # End of file
            break
        pos = 0
        while pos < len(data):
            pushed, avail, underruns = audioctx.put(data[pos:])
            if pushed == 0:
                await asyncio.sleep_ms(0)
            else:
                await asyncio.sleep_ms(0)
            pos += pushed
        if underruns > known_underruns:
            print(f"{underruns:x}")
            known_underruns = underruns
    audioctx.flush()
    print("Decoding ended")


async def play_mp3s(audiocore, mp3files):
    for name in mp3files:
        print(b'Playing ' + name)
        with open(name, "rb") as testfile:
            await play_mp3(audiocore, testfile)
        await asyncio.sleep_ms(1000)


# Set 8 mA drive strength and fast slew rate
machine.mem32[0x4001c004 + 6*4] = 0x67
machine.mem32[0x4001c004 + 7*4] = 0x67
machine.mem32[0x4001c004 + 8*4] = 0x67


def list_sd():
    try:
        sd = SDCard(mosi=Pin(3), miso=Pin(4), sck=Pin(2), ss=Pin(5), baudrate=15000000)
    except OSError:
        for i in range(leds):
            np[i] = (255, 0, 0)
        np.write()
        return
    try:
        os.mount(sd, '/sd')
        print(os.listdir(b'/sd'))
    except OSError as ex:
        print(f"{ex}")


delay_sum = 0
delay_count = 0
max_delay = 0


async def latency_test():
    global delay_sum
    global delay_count
    global max_delay
    await asyncio.sleep_ms(1)
    while True:
        for _ in range(2000):
            before = time.ticks_us()
            await asyncio.sleep(0)
            after = time.ticks_us()
            delay = after - before
            delay_sum += delay
            delay_count += 1
            if delay > max_delay:
                max_delay = delay
            await asyncio.sleep_ms(1)
        print(f"Max delay {max_delay} us, average {delay/delay_sum} us")

pin = Pin.board.GP16
np = NeoPixel(pin, leds)

# Test SD card
list_sd()

# Test NeoPixel
asyncio.create_task(rainbow(np))

# Test audio
audioctx = Audiocore(Pin(8), Pin(6))

# high prio for proc 1
machine.mem32[0x40030000 + 0x00] = 0x10

testfiles = [b'/sd/' + name for name in os.listdir(b'/sd') if name.endswith(b'mp3')]

asyncio.create_task(play_mp3s(audioctx, testfiles))

asyncio.create_task(aiorepl.task())
asyncio.get_event_loop().run_forever()
