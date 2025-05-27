# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import asyncio
import machine
import micropython
import time
try:
    from typing import TYPE_CHECKING  # type: ignore
except ImportError:
    TYPE_CHECKING = False
if TYPE_CHECKING:
    import typing

    class ButtonCallback(typing.Protocol):
        def onButtonPressed(self, what: int) -> None: ...


class Buttons:
    def __init__(self, cb: ButtonCallback, pin_volup=17, pin_voldown=19, pin_next=18):
        self.VOLUP = micropython.const(1)
        self.VOLDOWN = micropython.const(2)
        self.NEXT = micropython.const(3)
        self.cb = cb
        self.buttons = {machine.Pin(pin_volup, machine.Pin.IN, machine.Pin.PULL_UP): self.VOLUP,
                        machine.Pin(pin_voldown, machine.Pin.IN, machine.Pin.PULL_UP): self.VOLDOWN,
                        machine.Pin(pin_next, machine.Pin.IN, machine.Pin.PULL_UP): self.NEXT}
        self.int_flag = asyncio.ThreadSafeFlag()
        self.pressed: list[int] = []
        self.last: dict[int, int] = {}
        for button in self.buttons.keys():
            button.irq(handler=self._interrupt, trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING)
        asyncio.create_task(self.task())

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
                self.cb.onButtonPressed(what)
