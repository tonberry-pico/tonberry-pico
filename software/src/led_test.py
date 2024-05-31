# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

# Run with mpremote.py run src/led_test.py

from machine import Pin
from math import pi, sin, pow
from micropython import const
from rp2_neopixel import NeoPixel
from time import sleep, ticks_ms
import asyncio

pin = Pin.board.GP16
leds = const(10)
brightness = 0.5

np = NeoPixel(pin, leds)

# test fill and write

print("LEDs should now turn red")
np.fill((255, 0, 0))
np.write()
sleep(1)

print("LEDs should now turn green")
np.fill((0, 255, 0))
np.write()
sleep(1)

print("LEDs should now turn blue")
np.fill((0, 0, 255))
np.write()
sleep(1)


# test async
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
        before = ticks_ms()
        await np.async_write()
        now = ticks_ms()
        if before + 20 > now:
            await asyncio.sleep_ms(20 - (now - before))

print("LEDs should now start rainbowing")
asyncio.run(rainbow(np))
