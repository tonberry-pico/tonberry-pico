# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

from collections import namedtuple
import time
from utils import TimerManager


Dependencies = namedtuple('Dependencies', ('mp3player', 'nfcreader', 'buttons', 'playlistdb'))

# Should be ~ 6dB steps
VOLUME_CURVE = [1, 2, 4, 8, 16, 32, 63, 126, 251]


class PlayerApp:
    def __init__(self, deps: Dependencies):
        self.current_tag = None
        self.current_tag_time = time.ticks_ms()
        self.timer_manager = TimerManager()
        self.player = deps.mp3player(self)
        self.nfc = deps.nfcreader(self)
        self.playlist_db = deps.playlistdb(self)
        self.buttons = deps.buttons(self) if deps.buttons is not None else None
        self.mp3file = None
        self.volume_pos = 3
        self.player.set_volume(VOLUME_CURVE[self.volume_pos])

    def __del__(self):
        if self.mp3file is not None:
            self.mp3file.close()
            self.mp3file = None

    def onTagChange(self, new_tag):
        if new_tag is not None:
            self.timer_manager.cancel(self.onTagRemoveDelay)
        if new_tag == self.current_tag:
            return
        # Change playlist on new tag
        if new_tag is not None:
            self.current_tag_time = time.ticks_ms()
            self.current_tag = new_tag
            uid_str = b''.join('{:02x}'.format(x).encode() for x in new_tag)
            self._set_playlist(uid_str)
        else:
            self.timer_manager.schedule(time.ticks_ms() + 5000, self.onTagRemoveDelay)

    def onTagRemoveDelay(self):
        if self.current_tag is not None:
            print('Tag gone, stopping playback')
            self.current_tag = None
            self.player.stop()

    def onButtonPressed(self, what):
        assert self.buttons is not None
        if what == self.buttons.VOLUP:
            self.volume_pos = min(self.volume_pos + 1, len(VOLUME_CURVE) - 1)
            self.player.set_volume(VOLUME_CURVE[self.volume_pos])
        elif what == self.buttons.VOLDOWN:
            self.volume_pos = max(self.volume_pos - 1, 0)
            self.player.set_volume(VOLUME_CURVE[self.volume_pos])
        elif what == self.buttons.NEXT:
            self._play_next()

    def onPlaybackDone(self):
        assert self.mp3file is not None
        self.mp3file.close()
        self.mp3file = None
        self._play_next()

    def _set_playlist(self, tag: bytes):
        self.playlist = self.playlist_db.getPlaylistForTag(tag)
        self._play(self.playlist.getCurrentPath())

    def _play_next(self):
        if self.playlist is None:
            return
        filename = self.playlist.getNextPath()
        self._play(filename)
        if filename is None:
            self.playlist = None

    def _play(self, filename: bytes | None):
        if self.mp3file is not None:
            self.player.stop()
            self.mp3file.close()
            self.mp3file = None
        if filename is not None:
            print(f'Playing {filename!r}')
            self.mp3file = open(filename, 'rb')
            self.player.play(self.mp3file)
