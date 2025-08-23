# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

from machine import Pin

pins = [Pin.board.GP0,
        Pin.board.GP1,
        Pin.board.GP2,
        Pin.board.GP3,
        Pin.board.GP4,
        Pin.board.GP5,
        Pin.board.GP6,
        Pin.board.GP7,
        Pin.board.GP8,
        Pin.board.GP9,
        Pin.board.GP10,
        Pin.board.GP11,
        Pin.board.GP12,
        Pin.board.GP13,
        Pin.board.GP14,
        Pin.board.GP15,
        Pin.board.GP16,
        Pin.board.GP17,
        Pin.board.GP18,
        Pin.board.GP19,
        Pin.board.GP20,
        Pin.board.GP21,
        Pin.board.GP22,
        None,  # 23
        None,  # 24
        None,  # 25
        Pin.board.GP26,
        Pin.board.GP27,
        Pin.board.GP28,
        ]


def get_pin_index(pin: Pin) -> int:
    """
    Get the pin index back from a pin object.
    Unfortunately, micropython has no built-in function for this.
    """
    return pins.index(pin)
