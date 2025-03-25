'''
SPDX-License-Identifier: MIT
Copyright (c) 2025 Stefan Kratochwil (Kratochwil-LA@gmx.de)
'''

import asyncio
import time

from mfrc522 import MFRC522


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
    def __init__(self, reader: MFRC522):
        self.reader = reader
        self.last_uid = None
        self.last_uid_timestamp = None
        self.task = asyncio.create_task(self._reader_poll_task())

    @staticmethod
    def uid_to_string(uid: list):
        '''
        Helper function to convert a nfc tag uid to a readable string.
        '''
        return '0x' + ''.join(f'{i:02x}' for i in uid)

    async def _reader_poll_task(self, poll_interval_ms: int = 50):
        '''
        Periodically polls the nfc reader. Stores tag uid and timestamp if a new tag was found.
        '''
        while True:
            self.reader.init()

            # For now we omit the tag type
            (stat, _) = self.reader.request(self.reader.REQIDL)
            if stat == self.reader.OK:
                (stat, uid) = self.reader.SelectTagSN()
                if stat == self.reader.OK:
                    self.last_uid = uid
                    self.last_uid_timestamp = time.ticks_us()

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
