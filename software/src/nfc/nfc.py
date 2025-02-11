import asyncio
import time

from mfrc522 import MFRC522

class Nfc:
    def __init__(self):
        self.reader = MFRC522(spi_id=1, sck=10, miso=12, mosi=11, cs=13, rst=9, tocard_retries=10)
        self.last_uid = None
        self.last_uid_timestamp = None
        self.task = asyncio.create_task(self._reader_poll_task())


    @staticmethod
    def uid_to_string(uid: list):
        return '0x' + ''.join(f'{i:02x}' for i in uid)


    async def _reader_poll_task(self, poll_interval_ms: int = 50) -> list:
        print('reader_poll_task alive')

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
        return self.last_uid, self.last_uid_timestamp
