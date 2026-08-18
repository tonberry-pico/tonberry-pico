# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

from collections import namedtuple
import time
from utils import TimerManager


Dependencies = namedtuple('Dependencies', ('mp3player', 'nfcreader', 'buttons', 'playlistdb', 'hwconfig', 'leds',
                                           'config'))

# Should be ~ 3dB steps
VOLUME_CURVE = [1, 2, 3, 4, 6, 8, 11, 16, 23, 32, 45, 64, 91, 128, 181, 255]


# Unfortunately, we don't have enum in micropython
class PlaybackStates:
    NO_PLAYLIST = 0
    PLAYING = 1
    PAUSED = 2
    END_OF_PLAYLIST = 3

    @staticmethod
    def to_string(val):
        if val == PlaybackStates.NO_PLAYLIST:
            return "No Playlist"
        elif val == PlaybackStates.PLAYING:
            return "Playing"
        elif val == PlaybackStates.PAUSED:
            return "Paused"
        elif val == PlaybackStates.END_OF_PLAYLIST:
            return "End of playlist"
        else:
            return "INVALID"


class PlayerApp:
    class TagStateMachine:
        def __init__(self, parent, timer_manager, tag_mode, timeout=5000):
            self.parent = parent
            self.timer_manager = timer_manager
            self.current_tag = None
            self.last_tag = None
            self.tag_mode = tag_mode
            self.timeout = timeout

        #
        # Callbacks called by NFCReader
        #

        def onTagChange(self, new_tag):
            if new_tag is not None:
                self.timer_manager.cancel(self.onTagRemoveDelay)
            if new_tag == self.current_tag:
                return
            # Change playlist on new tag
            if new_tag is not None:
                self.current_tag = new_tag
                self._tag_new(new_tag)
            else:
                self.timer_manager.schedule(time.ticks_ms() + self.timeout, self.onTagRemoveDelay)

        def onTagRemoveDelay(self):
            if self.current_tag is not None:
                self.current_tag = None
                self._tag_gone()

        #
        # Handle 'real' tag changes after tagRemoveDelay debouncing
        #

        def _tag_new(self, new_tag):
            if self.tag_mode == 'tagremains':
                self.parent.onNewTag(new_tag)
            elif self.tag_mode == 'tagstartstop':
                if new_tag == self.last_tag:
                    self.parent.onTagRemoved()
                    self.last_tag = None
                else:
                    self.parent.onNewTag(new_tag)
                    self.last_tag = new_tag

        def _tag_gone(self):
            if self.tag_mode == 'tagremains':
                self.parent.onTagRemoved()
            elif self.tag_mode == 'tagstartstop':
                pass

        def clearLastTag(self):
            self.last_tag = None

    def __init__(self, deps: Dependencies):
        self.timer_manager = TimerManager()
        self.config = deps.config(self)
        self.tag_timeout_ms = self.config.get_tag_timeout() * 1000
        self.idle_timeout_ms = self.config.get_idle_timeout() * 1000
        self.tag_state_machine = self.TagStateMachine(self, self.timer_manager, self.config.get_tagmode(),
                                                      self.tag_timeout_ms)
        self.player = deps.mp3player(self)
        self.nfc = deps.nfcreader(self.tag_state_machine)
        self.playlist_db = deps.playlistdb(self)
        self.hwconfig = deps.hwconfig(self)
        self.leds = deps.leds(self)
        self.buttons = deps.buttons(self) if deps.buttons is not None else None
        self.volume_max = self.config.get_volume_max()
        self.volume_pos = 3  # fallback if config.get_volume_boot is nonsense
        try:
            for idx, val in enumerate(VOLUME_CURVE):
                if val >= self.config.get_volume_boot():
                    self.volume_pos = idx
                    break
        except (TypeError, ValueError):
            pass
        self.playback_state = PlaybackStates.NO_PLAYLIST
        self.playlist = None
        self.mp3file = None
        self.player.set_volume(VOLUME_CURVE[self.volume_pos])
        self._onIdle()

    def __del__(self):
        if self.mp3file is not None:
            self.mp3file.close()
            self.mp3file = None

    #
    # Handle NFC tag interactions
    #

    def onNewTag(self, new_tag):
        """
        Callback to signal that a new tag has been presented.
        """
        if self.playback_state in (PlaybackStates.PLAYING, PlaybackStates.PAUSED):
            self._st_playing_or_paused_TO_no_playlist()
        elif self.playback_state == PlaybackStates.END_OF_PLAYLIST:
            self._st_end_of_playlist_TO_no_playlist()
        self._st_no_playlist_TO_playing(new_tag)

    def onTagRemoved(self):
        """
        Callback to signal that a tag has been removed.
        """
        if self.playback_state in (PlaybackStates.PLAYING, PlaybackStates.PAUSED):
            self._st_playing_or_paused_TO_no_playlist()
        elif self.playback_state == PlaybackStates.END_OF_PLAYLIST:
            self._st_end_of_playlist_TO_no_playlist()

    #
    # Handle button interactions
    #

    def onButtonPressed(self, what):
        """
        Callback from the ButtonManager to signal that a button has been pressed.
        """
        assert self.buttons is not None
        if what == self.buttons.VOLUP:
            new_volume = min(self.volume_pos + 1, len(VOLUME_CURVE) - 1)
            if VOLUME_CURVE[new_volume] <= self.volume_max:
                self.volume_pos = new_volume
                self.player.set_volume(VOLUME_CURVE[self.volume_pos])
        elif what == self.buttons.VOLDOWN:
            self.volume_pos = max(self.volume_pos - 1, 0)
            self.player.set_volume(VOLUME_CURVE[self.volume_pos])
        elif what == self.buttons.NEXT:
            self._on_next_pressed()
        elif what == self.buttons.PREV:
            self._on_prev_pressed()
        elif what == self.buttons.PLAY_PAUSE:
            self._on_pause_pressed()

    def _on_next_pressed(self):
        if self.playback_state in (PlaybackStates.PLAYING, PlaybackStates.PAUSED):
            self._st_playing_or_paused_TO_playing(self.playlist.getNextPath())
        elif self.playback_state == PlaybackStates.END_OF_PLAYLIST:
            self._st_end_of_playlist_TO_playing(direction="next")

    def _on_prev_pressed(self):
        if self.playback_state in (PlaybackStates.PLAYING, PlaybackStates.PAUSED):
            self._st_playing_or_paused_TO_playing(self.playlist.getPrevPath())
        elif self.playback_state == PlaybackStates.END_OF_PLAYLIST:
            self._st_end_of_playlist_TO_playing(direction="prev")

    def _on_pause_pressed(self):
        if self.playback_state == PlaybackStates.PLAYING:
            self._st_playing_TO_paused()
        elif self.playback_state == PlaybackStates.PAUSED:
            self._st_paused_TO_playing()

    #
    # State transition methods
    #

    def _st_setstate(self, newstate, *dbgparams):
        print(f"PlayerApp ST: ({PlaybackStates.to_string(self.playback_state)}) -> "
              f"({PlaybackStates.to_string(newstate)}) {dbgparams}")
        if newstate == PlaybackStates.PLAYING and self.playback_state != PlaybackStates.PLAYING:
            self._onActive()
        elif newstate != PlaybackStates.PLAYING and self.playback_state == PlaybackStates.PLAYING:
            self._onIdle()
        self.playback_state = newstate

    def _st_no_playlist_TO_playing(self, tag: list[int]):
        """State transition from no playlist to playing

        Triggered by: New or changed tag

        Action: Load the new playlist and then play the current track as defined by the playlist. If
        no playlist exists for tag, remain in NO_PLAYLIST state.
        """
        uid_str = b''.join('{:02x}'.format(x).encode() for x in tag)
        self.playlist = self.playlist_db.getPlaylistForTag(uid_str)
        if not self.playlist:
            # No playlist for tag
            return
        self._play(self.playlist.getCurrentPath(), self.playlist.getPlaybackOffset())
        self._st_setstate(PlaybackStates.PLAYING, uid_str)

    def _st_playing_TO_end_of_playlist(self):
        """State transistion from playing to end of playlist

        Triggered by: indirectly when next track is None

        Action: Reset last tag in Tag State Machine. This is needed for tag-start-stop mode. If the
        previously played tag is presented again after the end of playlist state is reached, it
        should not be treated as a request to stop playback.
        """
        self.tag_state_machine.clearLastTag()
        self._st_setstate(PlaybackStates.END_OF_PLAYLIST)

    def _st_playing_TO_paused(self):
        """State transition from playing to paused

        Triggered by: Play/Pause pressed when in playing state

        Action: Pause playback
        """
        self.pause_offset = self._stop(save_pos=True)
        self._st_setstate(PlaybackStates.PAUSED)

    def _st_paused_TO_playing(self):
        """State transition from paused to playing

        Triggered by: Play/Pause pressed when in paused state

        Action: Resume playback
        """
        self._play(self.playlist.getCurrentPath(), self.pause_offset)
        self._st_setstate(PlaybackStates.PLAYING)

    def _st_playing_or_paused_TO_no_playlist(self):
        """State transition from playing or paused to no playlist

        Triggered by: Tag removed or changed

        Action: Stop playback and clear playlist
        """
        self._stop(save_pos=True)
        self.playlist = None
        self._st_setstate(PlaybackStates.NO_PLAYLIST)

    def _st_playing_or_paused_TO_playing(self, filename: str | None):
        """State transition from playing or paused to playing

        Triggered by: Track change during playback or in pause mode

        Action: Stop playback if playing, play new track. Go to end of playlist if new track filename is None
        """
        if filename is None:
            self._stop()
            print("PlayerApp ST: (Playing, Paused) -> (Playing) got filename None, redirecting to (End of playlist)")
            self._st_playing_TO_end_of_playlist()
        else:
            self._play(filename)
            self._st_setstate(PlaybackStates.PLAYING, filename)

    def _st_end_of_playlist_TO_no_playlist(self):
        """State transition from end of playlist to no playlist

        Triggered by: Tag removed or changed

        Action: clear playlist
        """
        self.playlist = None
        self._st_setstate(PlaybackStates.NO_PLAYLIST)

    def _st_end_of_playlist_TO_playing(self, direction: str):
        """State transition from end of playlist to no playlist

        Triggered by: Next or Prev button pressed after end of playlist was reached

        Action: Resume playback from first or last of playlist, depending on direction
        """
        if direction == "next":
            self.playlist.restart()
            filename = self.playlist.getCurrentPath()
        else:
            filename = self.playlist.getPrevPath()
        self._play(filename)
        self._st_setstate(PlaybackStates.PLAYING, direction, filename)

    #
    # Methods to manage actual playing of files and interactions with MP3Player
    #

    def _play(self, filename: bytes | None, offset=0):
        if self.mp3file is not None:
            self.player.stop()
            self.mp3file.close()
            self.mp3file = None
        print(f'Playing {filename!r}')
        try:
            self.mp3file = open(filename, 'rb')
        except OSError as ex:
            print(f"Could not play file {filename}: {ex}")
            return
        self.player.play(self.mp3file, offset)

    def _stop(self, save_pos=False):
        pos = self.player.stop()
        self.mp3file.close()
        self.mp3file = None
        if save_pos and pos is not None:
            self.playlist.setPlaybackOffset(pos)
        return pos

    def onPlaybackDone(self):
        """
        Callback from MP3Player to signal that the current track has reached its end.
        """
        if self.playback_state == PlaybackStates.PLAYING:
            self._st_playing_or_paused_TO_playing(self.playlist.getNextPath())

    #
    # Methods to manage idle timeout and LED state
    #

    def _onIdle(self):
        self.timer_manager.schedule(time.ticks_ms() + self.idle_timeout_ms, self.onIdleTimeout)
        self.leds.set_state(self.leds.IDLE)

    def _onActive(self):
        self.timer_manager.cancel(self.onIdleTimeout)
        self.leds.set_state(self.leds.PLAYING)

    def onIdleTimeout(self):
        if self.hwconfig.get_on_battery():
            self.hwconfig.power_off()
        else:
            # Check again in a minute
            self.timer_manager.schedule(time.ticks_ms() + self.idle_timeout_ms, self.onIdleTimeout)

    #
    # Public methods
    #

    def get_nfc(self):
        """
        Get the NFCReader instance of the PlayerApp.
        """
        return self.nfc

    def get_playlist_db(self):
        """
        Get the PlaylistDB instance of the PlayerApp.
        """
        return self.playlist_db

    def get_leds(self):
        """
        Get the LEDManager instance of the PlayerApp.
        """
        return self.leds

    def reset_idle_timeout(self):
        """
        Reset the idle timeout if the device is currently idle.
        """
        if not self.is_playing():
            self.timer_manager.schedule(time.ticks_ms() + self.idle_timeout_ms, self.onIdleTimeout)

    def is_playing(self) -> bool:
        """
        Check whether the device is currently playing.
        """
        return self.playback_state == PlaybackStates.PLAYING
