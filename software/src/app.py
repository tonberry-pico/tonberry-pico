# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

from collections import namedtuple
import time
from utils import TimerManager


Dependencies = namedtuple('Dependencies', ('mp3player', 'nfcreader', 'buttons', 'playlistdb', 'leds'))

# Should be ~ 6dB steps
VOLUME_CURVE = [1, 2, 4, 8, 16, 32, 63, 126, 251]


class PlayerApp:
    class TagStateMachine:
        def __init__(self, parent, timer_manager):
            self.parent = parent
            self.timer_manager = timer_manager
            self.current_tag = None
            self.current_tag_time = time.ticks_ms()

        def onTagChange(self, new_tag):
            if new_tag is not None:
                self.timer_manager.cancel(self.onTagRemoveDelay)
            if new_tag == self.current_tag:
                return
            # Change playlist on new tag
            if new_tag is not None:
                self.current_tag_time = time.ticks_ms()
                self.current_tag = new_tag
                self.parent.onNewTag(new_tag)
            else:
                self.timer_manager.schedule(time.ticks_ms() + 5000, self.onTagRemoveDelay)

        def onTagRemoveDelay(self):
            if self.current_tag is not None:
                self.current_tag = None
                self.parent.onTagRemoved()

    def __init__(self, deps: Dependencies):
        self.timer_manager = TimerManager()
        self.tag_state_machine = self.TagStateMachine(self, self.timer_manager)
        self.player = deps.mp3player(self)
        self.nfc = deps.nfcreader(self.tag_state_machine)
        self.playlist_db = deps.playlistdb(self)
        self.leds = deps.leds(self)
        self.tag_mode = self.playlist_db.getSetting('tagmode')
        self.playing_tag = None
        self.playlist = None
        self.buttons = deps.buttons(self) if deps.buttons is not None else None
        self.mp3file = None
        self.volume_pos = 3
        self.player.set_volume(VOLUME_CURVE[self.volume_pos])
        self._onIdle()

    def __del__(self):
        if self.mp3file is not None:
            self.mp3file.close()
            self.mp3file = None

    def onNewTag(self, new_tag):
        """
        Callback (typically called by TagStateMachine) to signal that a new tag has been presented.
        """
        uid_str = b''.join('{:02x}'.format(x).encode() for x in new_tag)
        if self.tag_mode == 'tagremains' or (self.tag_mode == 'tagstartstop' and new_tag != self.playing_tag):
            self._set_playlist(uid_str)
            self.playing_tag = new_tag
        elif self.tag_mode == 'tagstartstop':
            print('Tag presented again, stopping playback')
            self._unset_playlist()
            self.playing_tag = None

    def onTagRemoved(self):
        """
        Callback (typically called by TagStateMachine) to signal that a tag has been removed.
        """
        if self.tag_mode == 'tagremains':
            print('Tag gone, stopping playback')
            self._unset_playlist()

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
        if self.playlist is not None:
            pos = self.player.stop()
            if pos is not None:
                self.playlist.setPlaybackOffset(pos)
        self.playlist = self.playlist_db.getPlaylistForTag(tag)
        self._play(self.playlist.getCurrentPath() if self.playlist is not None else None,
                   self.playlist.getPlaybackOffset() if self.playlist is not None else 0)

    def _unset_playlist(self):
        if self.playlist is not None:
            pos = self.player.stop()
            self._onIdle()
            if pos is not None:
                self.playlist.setPlaybackOffset(pos)
            self.playlist = None

    def _play_next(self):
        if self.playlist is None:
            return
        filename = self.playlist.getNextPath()
        self._play(filename)
        if filename is None:
            self.playlist = None
            self.playing_tag = None

    def _play(self, filename: bytes | None, offset=0):
        if self.mp3file is not None:
            self.player.stop()
            self.mp3file.close()
            self.mp3file = None
            self._onIdle()
        if filename is not None:
            print(f'Playing {filename!r}')
            self.mp3file = open(filename, 'rb')
            self.player.play(self.mp3file, offset)
            self._onActive()

    def _onIdle(self):
        self.leds.set_state(self.leds.IDLE)

    def _onActive(self):
        self.leds.set_state(self.leds.PLAYING)
