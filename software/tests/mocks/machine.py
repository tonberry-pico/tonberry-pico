# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

class Pin:
    def __init__(self, idx):
        self.idx = idx

    board = None


class Board:
    GP0 = Pin(0)
    GP1 = Pin(1)
    GP2 = Pin(2)
    GP3 = Pin(3)
    GP4 = Pin(4)
    GP5 = Pin(5)
    GP6 = Pin(6)
    GP7 = Pin(7)
    GP8 = Pin(8)
    GP9 = Pin(9)
    GP10 = Pin(10)
    GP11 = Pin(11)
    GP12 = Pin(12)
    GP13 = Pin(13)
    GP14 = Pin(14)
    GP15 = Pin(15)
    GP16 = Pin(16)
    GP17 = Pin(17)
    GP18 = Pin(18)
    GP19 = Pin(19)
    GP20 = Pin(20)
    GP21 = Pin(21)
    GP22 = Pin(22)
    GP26 = Pin(26)
    GP27 = Pin(27)
    GP28 = Pin(28)


Pin.board = Board
