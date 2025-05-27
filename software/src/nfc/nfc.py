'''
SPDX-License-Identifier: MIT
Copyright (c) 2025 Stefan Kratochwil (Kratochwil-LA@gmx.de)
Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>
'''

import asyncio
import time

from mfrc522 import MFRC522
try:
    from typing import TYPE_CHECKING  # type: ignore
except ImportError:
    TYPE_CHECKING = False
if TYPE_CHECKING:
    import typing

    class TagCallback(typing.Protocol):
        def onTagChange(self, uid: list[int]) -> None: ...


class Nfc:
    '''
    This class implements an asyncio task which continuously polls the mfrc522 nfc reader. If a new
    nfc tag was detected, the uid of the tag is stored alongside with the current system time. This
    information can be retrieved again.

    Usage example:

    import asyncio
    from nfc import Nfc

    async def main():
        n = Nfc()
        while True:
            await asyncio.sleep_ms(500)
            print(f'{n.get_last_uid()}')

    asyncio.run(main())
    '''
    def __init__(self, reader: MFRC522, cb: TagCallback | None = None):
        self.reader = reader
        self.last_uid: list[int] | None = None
        self.last_uid_timestamp: int | None = None
        self.cb = cb
        self.task = asyncio.create_task(self._reader_poll_task())

    @staticmethod
    def uid_to_string(uid: list):
        '''
        Helper function to convert a nfc tag uid to a readable string.
        '''
        return '0x' + ''.join(f'{i:02x}' for i in uid)

    def _read_tag_sn(self) -> list[int] | None:
        (stat, _) = self.reader.request(self.reader.REQIDL)
        if stat == self.reader.OK:
            (stat, uid) = self.reader.SelectTagSN()
            if stat == self.reader.OK:
                return uid
        return None

    async def _reader_poll_task(self, poll_interval_ms: int = 50):
        '''
        Periodically polls the nfc reader. Stores tag uid and timestamp if a new tag was found.
        '''
        last_callback_uid = None
        while True:
            self.reader.init()

            # For now we omit the tag type
            uid = self._read_tag_sn()
            if uid is not None:
                self.last_uid = uid
                self.last_uid_timestamp = time.ticks_us()
            if self.cb is not None and last_callback_uid != uid:
                self.cb.onTagChange(uid)
                last_callback_uid = uid

            await asyncio.sleep_ms(poll_interval_ms)

    def get_last_uid(self):
        '''
        Returns the last read nfc tag uid alongside with the timestamp it was stored at.
        '''
        return self.last_uid, self.last_uid_timestamp


if __name__ == '__main__':
    async def main():
        reader = MFRC522(spi_id=1, sck=10, miso=12, mosi=11, cs=13, rst=9, tocard_retries=20)
        n = Nfc(reader=reader)
        while True:
            await asyncio.sleep_ms(500)
            print(f'{n.get_last_uid()}')

    asyncio.run(main())
