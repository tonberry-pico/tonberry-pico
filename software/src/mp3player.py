# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import asyncio
from array import array
from utils import TimerManager
try:
    from typing import TYPE_CHECKING  # type: ignore
except ImportError:
    TYPE_CHECKING = False
if TYPE_CHECKING:
    import typing

    class PlayerCallback(typing.Protocol):
        def onPlaybackDone(self) -> None: ...


class MP3Player:
    def __init__(self, audiocore, cb: PlayerCallback):
        self.audiocore = audiocore
        self.mp3task = None
        self.volume = 128
        self.cb = cb
        self.pos = 0

    def play(self, stream, offset=0):
        """
        Play from byte stream.
        If offset > 0, discard the first offset bytes
        """
        if self.mp3task is not None:
            self.mp3task.cancel()
            self.mp3task = None
        if offset > 0:
            stream.seek(offset, 1)
        self.pos = offset
        self.mp3task = asyncio.create_task(self._play_task(stream))

    def stop(self):
        """
        Stop playback
        """
        if self.mp3task is not None:
            self.mp3task.cancel()
            self.mp3task = None
            return self.pos
        return None

    def set_volume(self, volume: int):
        """
        Set volume (0..255).
        """
        self.volume = volume
        self.audiocore.set_volume(volume)

    def get_volume(self) -> int:
        return self.volume

    async def _play_task(self, stream):
        known_underruns = 0
        send_done = False
        data = array('b', range(512))
        try:
            while True:
                bytes_read = stream.readinto(data)
                if bytes_read == 0:
                    # End of file
                    break
                _, _, underruns = await self.audiocore.async_put(data[:bytes_read])
                self.pos += bytes_read
                if underruns > known_underruns:
                    print(f"{underruns:x}")
                    known_underruns = underruns
            # Call onPlaybackDone after flush
            send_done = True
        finally:
            await self.audiocore.async_flush()
        if send_done:
            # Only call onPlaybackDone if exit due to end of stream
            # Use timer with time 0 to call callback "immediately" but from a different task
            TimerManager().schedule(0, self.cb.onPlaybackDone)
