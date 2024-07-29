# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

import aiorepl
import asyncio
import audiocore
import machine
import micropython
import os
import time
from array import array
from machine import Pin, SPI
from math import pi, sin, pow
from micropython import const
from rp2_neopixel import NeoPixel
from sdcard import SDCard

micropython.alloc_emergency_exception_buf(100)

asyncio.create_task(aiorepl.task())

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


samplerate = 44100
hz = 441
count = 100
amplitude = 0x1fff
buf = array('I', range(count))
for i in range(len(buf)):
    val = int(sin(i * hz / samplerate * 2 * pi)*amplitude) & 0xffff
    buf[i] = (val << 16) | val


async def output_sound(audioctx):
    pos = 0
    known_underruns = 0
    while True:
        pushed, avail, underruns = audioctx.put(buf[pos:])
        pos = (pos + pushed) % len(buf)
        # print(f"pushed {pushed}, pos {pos}, avail {avail}")
        if underruns > known_underruns:
            print(f"{underruns:x}")
            known_underruns = underruns
        await asyncio.sleep(0)


# Set 8 mA drive strength and fast slew rate
machine.mem32[0x4001c004 + 6*4] = 0x67
machine.mem32[0x4001c004 + 7*4] = 0x67
machine.mem32[0x4001c004 + 8*4] = 0x67


def list_sd():
    sd_spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    try:
        sd = SDCard(sd_spi, Pin(5), 25000000)
    except OSError:
        for i in range(leds):
            np[i] = (255, 0, 0)
        np.write()
        return
    try:
        os.mount(sd, '/sd')
        print(os.listdir('/sd'))
    except OSError:
        pass


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
audioctx = audiocore.init(Pin(8), Pin(6), samplerate)
asyncio.create_task(output_sound(audioctx))

asyncio.create_task(latency_test())

asyncio.get_event_loop().run_forever()
