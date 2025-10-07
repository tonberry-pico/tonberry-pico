# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import _audiocore
from asyncio import ThreadSafeFlag
from utils import get_pin_index


class Audiocore:
    def __init__(self, din, dclk, lrclk):
        # PIO requires sideset pins to be adjacent
        assert get_pin_index(lrclk) == get_pin_index(dclk)+1 or get_pin_index(lrclk) == get_pin_index(dclk)-1
        self.notify = ThreadSafeFlag()
        self._audiocore = _audiocore.Audiocore(din, dclk, lrclk, self._interrupt)

    def deinit(self):
        self._audiocore.deinit()

    def _interrupt(self, _):
        self.notify.set()

    def flush(self):
        self._audiocore.flush()

    def set_volume(self, volume):
        self._audiocore.set_volume(volume)

    def put(self, buffer, blocking=False):
        pos = 0
        while True:
            (copied, buf_space, underruns) = self._audiocore.put(buffer[pos:])
            pos += copied
            if pos >= len(buffer) or not blocking:
                return (pos, buf_space, underruns)

    async def async_put(self, buffer):
        pos = 0
        while True:
            (copied, buf_space, underruns) = self._audiocore.put(buffer[pos:])
            pos += copied
            if pos >= len(buffer):
                return (pos, buf_space, underruns)
            await self.notify.wait()


class AudioContext:
    def __init__(self, din, dclk, lrclk):
        self.din = din
        self.dclk = dclk
        self.lrclk = lrclk

    def __enter__(self):
        self._audiocore = Audiocore(self.din, self.dclk, self.lrclk)
        return self._audiocore

    def __exit__(self, exc_type, exc_value, traceback):
        self._audiocore.deinit()
