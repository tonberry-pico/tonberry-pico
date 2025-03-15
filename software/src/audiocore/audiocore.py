import _audiocore
from asyncio import ThreadSafeFlag


class Audiocore:
    def __init__(self, pin, sideset):
        self.notify = ThreadSafeFlag()
        self._audiocore = _audiocore.Audiocore(pin, sideset, self._interrupt)

    def __del__(self):
        self._audiocore.deinit()

    def _interrupt(self, _):
        self.notify.set()

    def flush(self):
        self._audiocore.flush()

    def set_volume(self, volume):
        self._audiocore.set_volume(volume)

    def put(self, buffer, blocking=False):
        pos = 0
        while True:
            (copied, buf_space, underruns) = self._audiocore.put(buffer[pos:])
            pos += copied
            if pos >= len(buffer) or not blocking:
                return (pos, buf_space, underruns)

    async def async_put(self, buffer):
        pos = 0
        while True:
            (copied, buf_space, underruns) = self._audiocore.put(buffer[pos:])
            pos += copied
            if pos >= len(buffer):
                return (pos, buf_space, underruns)
            await self.notify.wait()
