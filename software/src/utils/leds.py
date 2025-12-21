# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import asyncio
from math import sin, pi
from micropython import const
import time


class LedManager:
    IDLE = const(0)
    PLAYING = const(1)
    REBOOTING = const(2)

    def __init__(self, np):
        self.led_state = LedManager.IDLE
        self.np = np
        self.brightness = 0.1
        self.leds = len(self.np)
        asyncio.create_task(self.run())

    def set_state(self, state):
        assert state in [LedManager.IDLE, LedManager.PLAYING, LedManager.REBOOTING]
        self.led_state = state

    def _gamma(self, value, X=2.2):
        result = min(max(int(self.brightness * pow(value / 255.0, X) * 255.0 + 0.5), 0), 255)
        if value > 0:
            result = max(1, result)
        return result

    def _rainbow(self, time):
        for i in range(self.leds):
            ofs = (time * self.leds + i) % self.leds
            self.np[i] = (self._gamma((sin(ofs / self.leds * 2 * pi) + 1) * 127),
                          self._gamma((sin(ofs / self.leds * 2 * pi + 2/3*pi) + 1) * 127),
                          self._gamma((sin(ofs / self.leds * 2 * pi + 4/3*pi) + 1) * 127))

    def _pulse(self, time, color, speed):
        scaled_sin = max(1, abs(sin(time / speed * 2 * pi)) * 255)
        val = (self._gamma(color[0]*scaled_sin),
               self._gamma(color[1]*scaled_sin),
               self._gamma(color[2]*scaled_sin))
        for i in range(self.leds):
            self.np[i] = val

    async def run(self):
        time_ = 0.0
        while True:
            if self.led_state == LedManager.IDLE:
                self._pulse(time_, (0, 1, 0), 3)
            elif self.led_state == LedManager.PLAYING:
                self._rainbow(time_)
            elif self.led_state == LedManager.REBOOTING:
                self._pulse(time_, (1, 0, 1), 0.2)
            time_ += 0.02
            before = time.ticks_ms()
            await self.np.async_write()
            now = time.ticks_ms()
            if before + 20 > now:
                await asyncio.sleep_ms(20 - (now - before))
