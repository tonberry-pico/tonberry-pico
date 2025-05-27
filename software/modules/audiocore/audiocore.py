import _audiocore
from asyncio import ThreadSafeFlag


class Audiocore:
    def __init__(self, pin, sideset):
        self.notify = ThreadSafeFlag()
        self.pin = pin
        self.sideset = sideset
        self._audiocore = _audiocore.Audiocore(self.pin, self.sideset, self._interrupt)

    def deinit(self):
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


class AudioContext:
    def __init__(self, pin, sideset):
        self.pin = pin
        self.sideset = sideset

    def __enter__(self):
        self._audiocore = Audiocore(self.pin, self.sideset)
        return self._audiocore

    def __exit__(self, exc_type, exc_value, traceback):
        self._audiocore.deinit()
