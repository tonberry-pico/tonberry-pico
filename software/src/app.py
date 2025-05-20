# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

from collections import namedtuple
import os
import time
from utils import TimerManager


Dependencies = namedtuple('Dependencies', ('mp3player', 'nfcreader', 'buttons'))

# Should be ~ 6dB steps
VOLUME_CURVE = [1, 2, 4, 8, 16, 32, 63, 126, 251]


class PlayerApp:
    def __init__(self, deps: Dependencies):
        self.current_tag = None
        self.current_tag_time = time.ticks_ms()
        self.timer_manager = TimerManager()
        self.player = deps.mp3player(self)
        self.nfc = deps.nfcreader(self)
        self.buttons = deps.buttons(self) if deps.buttons is not None else None
        self.volume_pos = 3
        self.player.set_volume(VOLUME_CURVE[self.volume_pos])

    def onTagChange(self, new_tag):
        if new_tag is not None:
            self.timer_manager.cancel(self.onTagRemoveDelay)
        if new_tag == self.current_tag:
            return
        # Change playlist on new tag
        if new_tag is not None:
            self.current_tag_time = time.ticks_ms()
            self.current_tag = new_tag
            uid_str = ''.join('{:02x}'.format(x) for x in new_tag)
            try:
                testfiles = [f'/sd/{uid_str}/'.encode() + name for name in os.listdir(f'/sd/{uid_str}'.encode())
                             if name.endswith(b'mp3')]
            except OSError as ex:
                print(f'Could not get playlist for tag {uid_str}: {ex}')
                self.current_tag = None
                self.player.stop()
                return
            testfiles.sort()
            self.player.set_playlist(testfiles)
        else:
            self.timer_manager.schedule(time.ticks_ms() + 5000, self.onTagRemoveDelay)

    def onTagRemoveDelay(self):
        if self.current_tag is not None:
            print('Tag gone, stopping playback')
            self.current_tag = None
            self.player.stop()

    def onButtonPressed(self, what):
        if what == self.buttons.VOLUP:
            self.volume_pos = min(self.volume_pos + 1, len(VOLUME_CURVE) - 1)
            self.player.set_volume(VOLUME_CURVE[self.volume_pos])
        elif what == self.buttons.VOLDOWN:
            self.volume_pos = max(self.volume_pos - 1, 0)
            self.player.set_volume(VOLUME_CURVE[self.volume_pos])
        elif what == self.buttons.NEXT:
            self.player.play_next()
