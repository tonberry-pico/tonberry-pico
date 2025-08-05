# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

from array import array
import struct


class MBRPartition:
    def __init__(self, bdev, partno):
        assert partno >= 0 and partno < 4
        self.bdev = bdev
        bdev_len = bdev.ioctl(4, None)
        bdev_bs = bdev.ioctl(5, None)
        assert bdev_bs == 512
        mbr = array('B', 512*b'0')
        bdev.readblocks(0, mbr)
        if mbr[510] != 0x55 or mbr[511] != 0xaa:
            raise ValueError("Not a valid MBR")
        partofs = 0x1be + partno*16
        (boot_ind, _, _, _,
         parttype, _, _, _,
         lba_start, lba_len) = struct.unpack_from('<BBBBBBBBLL', mbr, partofs)
        print(f'Partition {partno} bi {boot_ind} type {parttype} start {lba_start} len {lba_len}')
        if (boot_ind != 0x00 and boot_ind != 0x80) or parttype == 0x00:
            raise ValueError("Not a valid partition")
        self.offset = lba_start
        self.size = lba_len
        assert lba_start + lba_len <= bdev_len

    def ioctl(self, op, arg):
        if op == 4:
            return self.size
        elif op == 5:
            return 512
        else:
            return None

    def readblocks(self, block, buf):
        if block >= self.size:
            raise ValueError("Block out of range")
        return self.bdev.readblocks(block+self.offset, buf)

    def writeblocks(self, block, buf):
        if block >= self.size:
            raise ValueError("Block out of range")
        return self.bdev.writeblocks(block+self.offset, buf)
