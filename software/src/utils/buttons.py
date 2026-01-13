# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import asyncio
import machine
import micropython
import time
from utils import safe_callback, TimerManager
try:
    from typing import TYPE_CHECKING  # type: ignore
except ImportError:
    TYPE_CHECKING = False
if TYPE_CHECKING:
    import typing

    class ButtonCallback(typing.Protocol):
        def onButtonPressed(self, what: int) -> None: ...


class Buttons:
    VOLUP = micropython.const(1)
    VOLDOWN = micropython.const(2)
    NEXT = micropython.const(3)
    PREV = micropython.const(4)
    PLAY_PAUSE = micropython.const(5)
    KEYMAP = {VOLUP: 'VOLUP',
              VOLDOWN: 'VOLDOWN',
              NEXT: 'NEXT',
              PREV: 'PREV',
              PLAY_PAUSE: 'PLAY_PAUSE'}

    def __init__(self, cb: "ButtonCallback", config, hwconfig):
        self.button_map = config.get_button_map()
        self.hw_buttons = hwconfig.BUTTONS
        self.hwconfig = hwconfig
        self.cb = cb
        self.buttons = dict()
        for key_id, key_name in self.KEYMAP.items():
            pin = self._get_pin(key_name)
            if pin is None:
                continue
            self.buttons[pin] = key_id
        self.int_flag = asyncio.ThreadSafeFlag()
        self.pressed: list[int] = []
        self.last: dict[int, int] = {}
        self.timer_manager = TimerManager()
        for button in self.buttons.keys():
            button.irq(handler=self._interrupt, trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING)
        asyncio.create_task(self.task())

    def _get_pin(self, key):
        key_id = self.button_map.get(key, None)
        if key_id is None:
            return None
        if key_id < 0 or key_id >= len(self.hw_buttons):
            return None
        pin = self.hw_buttons[key_id]
        if pin is not None:
            pin.init(machine.Pin.IN, machine.Pin.PULL_UP)
        return pin

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
            if keycode == self.VOLDOWN:
                self.timer_manager.schedule(time.ticks_ms() + 5000, self.long_press_shutdown)
        if button.value() == 1 and keycode == self.VOLDOWN:
            self.timer_manager.cancel(self.long_press_shutdown)

    async def task(self):
        while True:
            await self.int_flag.wait()
            while len(self.pressed) > 0:
                what = self.pressed.pop()
                safe_callback(lambda: self.cb.onButtonPressed(what), "button callback")

    def long_press_shutdown(self):
        if self.hwconfig.get_on_battery():
            self.hwconfig.power_off()
        else:
            machine.reset()
