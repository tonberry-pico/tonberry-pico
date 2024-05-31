# (mostly) drop-in replacement for micropython-lib NeoPixel driver using the RP2 PIO
# Makes rainbows go faster
# MIT license; Copyright (c) 2016 Damien P. George, 2021 Jim Mussared, 2024 Matthias Blankertz

from array import array
from asyncio import ThreadSafeFlag
from rp2 import StateMachine, asm_pio, PIO, DMA


# Based on pico-examples/pio/ws2812/ws2812.pio
# Copyright (c) 2020 Raspberry Pi (Trading) Ltd.
# SPDX-License-Identifier: BSD-3-Clause
T1 = 2
T2 = 5
T3 = 3

@asm_pio(sideset_init=(PIO.OUT_LOW), fifo_join=PIO.JOIN_TX, autopull=True,
         out_shiftdir=PIO.SHIFT_LEFT)
def _ws2812_pio(T1=T1, T2=T2, T3=T3):
    label("bitloop")
    out(x, 1).side(0).delay(T3-1)
    jmp(not_x, "do_zero").side(1) [T1-1]
    label("do_one")
    jmp("bitloop").side(1) [T2-1]
    label("do_zero")
    nop().side(0) [T2-1]
    wrap()


class NeoPixel:
    # G R B W
    ORDER = (2, 3, 1, 0)

    # User must set 'sm' to id of an unused PIO statemachine (range 0 to 7), as unfortunately the micropython API does
    # not expose the pico sdks claim functionality
    def __init__(self, pin, n, bpp=3, timing=1, sm=0):
        # Timing arg can be either 1 for 800 kHz, 0 for 400 kHz or a number x > 1 for x Hz
        if not isinstance(timing, int):
            raise ValueError("user-specified timing not supported")
        self.pin = pin
        self.n = n
        self.bpp = bpp
        self.buf = array('I', [0] * n)
        bitrate = (800000 if timing == 1 else
                   400000 if timing == 0 else
                   timing)
        self.statemachine = StateMachine(sm, _ws2812_pio,
                                         freq=bitrate*(T1+T2+T3),
                                         sideset_base=pin,
                                         pull_thresh=(32 if bpp == 4 else 24))
        self.statemachine.active(1)
        self.dma = DMA()
        self.dma_ctrl = self.dma.pack_ctrl(inc_write=False, treq_sel=(sm if sm <= 3 else 4+sm), irq_quiet=False)
        self.dma.irq(handler=self._interrupt)
        self.interrupt_flag = ThreadSafeFlag()

    def _interrupt(self, _):
        self.interrupt_flag.set()

    def __len__(self):
        return self.n

    def __setitem__(self, i, v):
        self.buf[i] = 0
        for b in range(self.bpp):
            self.buf[i] |= v[b] << (self.ORDER[b] * 8)

    def __getitem__(self, i):
        return tuple((self.buf[i] >> (self.ORDER[b] * 8)) & 0xff for b in range(self.bpp))

    def fill(self, v):
        val = 0
        for b in range(self.bpp):
            val |= v[b] << (self.ORDER[b] * 8)
        self.buf = array('I', [val]*self.n)

    def write(self):
        self.statemachine.put(self.buf)

    async def async_write(self):
        self.dma.config(read=self.buf, write=self.statemachine, count=self.n, ctrl=self.dma_ctrl, trigger=True)
        while self.dma.active():
            await self.interrupt_flag.wait()
