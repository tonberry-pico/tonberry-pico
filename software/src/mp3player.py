# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import asyncio
from array import array


class MP3Player:
    def __init__(self, audiocore):
        self.audiocore = audiocore
        self.commands = []
        self.command_event = asyncio.Event()
        self.playlist = []
        self.mp3task = None
        self.volume = 128

    def set_playlist(self, mp3files):
        """
        Set a new playlist and start playing from the first entry.
        For convenience a single file name can also be passed.
        """
        if type(mp3files) is bytes:
            self.playlist = [mp3files]
        else:
            self.playlist = mp3files
        self._send_command('newplaylist')

    def play_next(self):
        """
        Skip to the next track in the playlist. Reaching the end of the playlist stops playback.
        """
        self._send_command('next')

    def play_prev(self):
        """
        Skip to the previous track in the playlist.
        """
        self._send_command('prev')

    def stop(self):
        """
        Stop playback, remembering the current position in the playlist (but not inside a track).
        """
        self._send_command('stop')

    def play(self):
        """
        Start playback.
        """
        self._send_command('play')

    def set_volume(self, volume: int):
        """
        Set volume (0..255).
        """
        self.volume = volume
        self.audiocore.set_volume(volume)

    def get_volume(self) -> int:
        return self.volume

    def _send_command(self, command: str):
        self.commands.append(command)
        self.command_event.set()

    async def _play_task(self, mp3path):
        known_underruns = 0
        data = array('b', range(512))
        try:
            print(b'Playing ' + mp3path)
            with open(mp3path, 'rb') as mp3file:
                while True:
                    bytes_read = mp3file.readinto(data)
                    if bytes_read == 0:
                        # End of file
                        break
                    _, _, underruns = await self.audiocore.async_put(data[:bytes_read])
                    if underruns > known_underruns:
                        print(f"{underruns:x}")
                        known_underruns = underruns
            # Intentionally do not use _send_command, we don't want to set command_event yet
            self.commands.append('done')
        finally:
            self.audiocore.flush()
        self.command_event.set()

    def _play(self, mp3path):
        if self.mp3task is not None:
            self.mp3task.cancel()
            self.mp3task = None
        if mp3path is not None:
            self.mp3task = asyncio.create_task(self._play_task(mp3path))

    async def task(self):
        playlist_pos = 0
        while True:
            await self.command_event.wait()
            self.command_event.clear()
            change_play = False
            while len(self.commands) > 0:
                command = self.commands.pop()
                if command == 'next' or command == 'done':
                    if playlist_pos + 1 < len(self.playlist):
                        playlist_pos += 1
                        change_play = True
                    else:
                        # reaching the end of the playlist stops playback
                        self._play(None)
                elif command == 'prev':
                    if playlist_pos > 0:
                        playlist_pos -= 1
                    change_play = True
                elif command == 'stop':
                    self._play(None)
                elif command == 'play':
                    if self.mp3task is None:
                        change_play = True
                elif command == 'newplaylist':
                    if len(self.playlist) > 0:
                        playlist_pos = 0
                        change_play = True
                    else:
                        self._play(None)
            if change_play:
                self._play(self.playlist[playlist_pos])
