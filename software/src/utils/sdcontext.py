# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import os

from . import MBRPartition
from rp2_sd import SDCard


class SDContext:
    def __init__(self, mosi, miso, sck, ss, baudrate):
        self.mosi = mosi
        self.miso = miso
        self.sck = sck
        self.ss = ss
        self.baudrate = baudrate

    def __enter__(self):
        self.sdcard = SDCard(self.mosi, self.miso, self.sck, self.ss, self.baudrate)
        # Try first partition
        try:
            self.part = MBRPartition(self.sdcard, 0)
            os.mount(self.part, '/sd')
            return self
        except Exception:
            print("Failed to mount SDCard partition, trying whole device...")
        # Try whole device
        try:
            os.mount(self.sdcard, '/sd')
            return self
        except Exception as ex:
            self.sdcard.deinit()
            raise RuntimeError("Could not mount SD card") from ex

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            os.umount('/sd')
        finally:
            self.sdcard.deinit()
