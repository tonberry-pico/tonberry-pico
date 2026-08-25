# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import app
import builtins
import pytest  # type: ignore
import time
import utils


@pytest.fixture
def micropythonify():
    def time_ticks_ms():
        return time.time_ns() // 1000000
    time.ticks_ms = time_ticks_ms
    yield
    del time.ticks_ms


class FakeFile:
    def __init__(self, filename, mode):
        self.filename = filename
        self.mode = mode
        self.closed = False

    def close(self):
        self.closed = True


class FakeMp3Player:
    def __init__(self):
        self.volume: int | None = None
        self.track: FakeFile | None = None

    def set_volume(self, vol: int):
        self.volume = vol

    def play(self, track: FakeFile, offset: int):
        self.track = track

    def stop(self):
        self.track = None


class FakeTimerManager:
    def __init__(self):
        self.queued = []

    def cancel(self, timer):
        self.queued = [(elem[0], elem[1], True) if elem[1] == timer else elem for elem in self.queued]

    def schedule(self, when, what):
        self.queued.append((when, what, False))

    def testing_run_queued(self):
        queued = self.queued
        self.queued = []
        for when, what, canceled in queued:
            if not canceled:
                what()


class FakeNfcReader:
    tag_callback = None

    def __init__(self, tag_callback=None):
        FakeNfcReader.tag_callback = tag_callback


class FakeButtons:
    VOLUP = 1
    VOLDOWN = 2
    NEXT = 3
    PREV = 4
    PLAY_PAUSE = 5

    def __init__(self): pass


class FakePlaylistDb:
    class FakePlaylist:
        def __init__(self, parent, pos=0):
            self.parent = parent
            self.pos = 0

        def getCurrentPath(self):
            return self.parent.tracklist[self.pos]

        def getNextPath(self):
            self.pos += 1
            if self.pos >= len(self.parent.tracklist):
                self.pos = len(self.parent.tracklist)
                return None
            return self.parent.tracklist[self.pos]

        def getPrevPath(self):
            if self.pos > 0:
                self.pos -= 1
            return self.getCurrentPath()

        def getPlaybackOffset(self):
            return 0

        def restart(self):
            self.pos = 0

    def __init__(self, tracklist=[b'test/path.mp3']):
        self.tracklist = tracklist

    def getPlaylistForTag(self, tag: bytes):
        return self.FakePlaylist(self)

    def getSetting(self, key: bytes | str):
        if key == 'tagmode':
            return 'tagremains'
        return None


class FakeHwconfig:
    def __init__(self):
        self.powered = True
        self.on_battery = False

    def power_off(self):
        self.powered = False

    def get_on_battery(self):
        return self.on_battery


class FakeLeds:
    IDLE = 0
    PLAYING = 1

    def __init__(self):
        self.state = None

    def set_state(self, state):
        self.state = state


class FakeConfig:
    def __init__(self): pass

    def get_led_count(self):
        return 1

    def get_idle_timeout(self):
        return 60

    def get_tag_timeout(self):
        return 5

    def get_tagmode(self):
        return 'tagremains'

    def get_volume_max(self):
        return 255

    def get_volume_boot(self):
        return 16


def fake_open(filename, mode):
    return FakeFile(filename, mode)


@pytest.fixture
def faketimermanager(monkeypatch):
    fake_timer_manager = FakeTimerManager()
    monkeypatch.setattr(utils.timer.TimerManager, '_instance', fake_timer_manager)
    yield fake_timer_manager


def _makedeps(mp3player=FakeMp3Player, nfcreader=FakeNfcReader, buttons=FakeButtons,
              playlistdb=FakePlaylistDb, hwconfig=FakeHwconfig, leds=FakeLeds, config=FakeConfig):
    return app.Dependencies(mp3player=lambda _: mp3player() if callable(mp3player) else mp3player,
                            nfcreader=lambda x: nfcreader(x) if callable(nfcreader) else nfcreader,
                            buttons=lambda _: buttons() if callable(buttons) else buttons,
                            playlistdb=lambda _: playlistdb() if callable(playlistdb) else playlistdb,
                            hwconfig=lambda _: hwconfig() if callable(hwconfig) else hwconfig,
                            leds=lambda _: leds() if callable(leds) else leds,
                            config=lambda _: config() if callable(config) else config)


def test_construct_app(micropythonify, faketimermanager):
    fake_mp3 = FakeMp3Player()
    deps = _makedeps(mp3player=fake_mp3)
    dut = app.PlayerApp(deps)
    fake_mp3 = dut.player
    assert fake_mp3.volume is not None and fake_mp3.volume >= 16


def test_load_playlist_on_tag(micropythonify, faketimermanager, monkeypatch):
    fake_db = FakePlaylistDb()
    fake_mp3 = FakeMp3Player()
    deps = _makedeps(mp3player=fake_mp3, playlistdb=fake_db)
    app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'test/path.mp3'
        assert "r" in fake_mp3.track.mode
        assert "b" in fake_mp3.track.mode


def test_playlist_seq(micropythonify, faketimermanager, monkeypatch):
    fake_db = FakePlaylistDb([b'track1.mp3', b'track2.mp3', b'track3.mp3'])
    fake_mp3 = FakeMp3Player()
    deps = _makedeps(mp3player=fake_mp3, playlistdb=fake_db)
    dut = app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track1.mp3'

        fake_mp3.track = None
        dut.onPlaybackDone()
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track2.mp3'

        fake_mp3.track = None
        dut.onPlaybackDone()
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track3.mp3'

        fake_mp3.track = None
        dut.onPlaybackDone()
        assert fake_mp3.track is None


def test_playlist_unknown_tag(micropythonify, faketimermanager, monkeypatch):
    class FakeNoPlaylistDb:
        def getPlaylistForTag(self, tag):
            return None

        def getSetting(self, key: bytes | str):
            return None

    fake_db = FakeNoPlaylistDb()
    fake_mp3 = FakeMp3Player()
    deps = _makedeps(mp3player=fake_mp3, playlistdb=fake_db)
    app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is None


def test_tagmode_startstop(micropythonify, faketimermanager, monkeypatch):
    class FakeStartStopConfig(FakeConfig):
        def __init__(self):
            super().__init__()

        def get_tagmode(self):
            return 'tagstartstop'

    fake_db = FakePlaylistDb([b'test/path.mp3'])
    fake_mp3 = FakeMp3Player()
    deps = _makedeps(mp3player=fake_mp3, playlistdb=fake_db, config=FakeStartStopConfig)
    app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        # Present tag to start playback
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'test/path.mp3'
        # Removing tag should not stop playback
        FakeNfcReader.tag_callback.onTagChange(None)
        faketimermanager.testing_run_queued()
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'test/path.mp3'
        # Presenting tag should stop playback
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is None
        # Nothing should change here
        FakeNfcReader.tag_callback.onTagChange(None)
        faketimermanager.testing_run_queued()
        assert fake_mp3.track is None
        # Presenting tag again should start playback again
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'test/path.mp3'


def test_tagmode_remains(micropythonify, faketimermanager, monkeypatch):
    fake_db = FakePlaylistDb([b'test/path.mp3'])
    fake_mp3 = FakeMp3Player()
    deps = _makedeps(mp3player=fake_mp3, playlistdb=fake_db)
    app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        # Present tag to start playback
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'test/path.mp3'
        # Remove tag to stop playback
        FakeNfcReader.tag_callback.onTagChange(None)
        faketimermanager.testing_run_queued()
        assert fake_mp3.track is None
        # Presenting tag again should start playback again
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'test/path.mp3'


def test_led_state(micropythonify, faketimermanager, monkeypatch):
    fake_leds = FakeLeds()
    deps = _makedeps(leds=fake_leds)
    app.PlayerApp(deps)
    assert fake_leds.state == FakeLeds.IDLE
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_leds.state == FakeLeds.PLAYING
        FakeNfcReader.tag_callback.onTagChange(None)
        faketimermanager.testing_run_queued()
        assert fake_leds.state == FakeLeds.IDLE


def test_idle_shutdown_after_start(micropythonify, faketimermanager, monkeypatch):
    fake_hwconfig = FakeHwconfig()
    fake_hwconfig.on_battery = True
    deps = _makedeps(hwconfig=fake_hwconfig)
    app.PlayerApp(deps)
    assert fake_hwconfig.powered
    faketimermanager.testing_run_queued()
    assert not fake_hwconfig.powered


def test_idle_shutdown_after_playback(micropythonify, faketimermanager, monkeypatch):
    fake_hwconfig = FakeHwconfig()
    fake_hwconfig.on_battery = True
    deps = _makedeps(hwconfig=fake_hwconfig)
    app.PlayerApp(deps)
    assert fake_hwconfig.powered
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        faketimermanager.testing_run_queued()
        assert fake_hwconfig.powered
        # Stop playback
        FakeNfcReader.tag_callback.onTagChange(None)
        faketimermanager.testing_run_queued()
        # Elapse idle timer
        faketimermanager.testing_run_queued()
        assert not fake_hwconfig.powered


def test_next_restarts_finished_playlist(micropythonify, faketimermanager, monkeypatch):
    fake_db = FakePlaylistDb([b'track1.mp3', b'track2.mp3'])
    fake_mp3 = FakeMp3Player()
    deps = _makedeps(mp3player=fake_mp3, playlistdb=fake_db)
    dut = app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track1.mp3'

        fake_mp3.track = None
        dut.onPlaybackDone()
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track2.mp3'

        fake_mp3.track = None
        dut.onPlaybackDone()
        assert fake_mp3.track is None

        dut.onButtonPressed(FakeButtons.NEXT)
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track1.mp3'


def test_next_plays_next_track(micropythonify, faketimermanager, monkeypatch):
    fake_db = FakePlaylistDb([b'track1.mp3', b'track2.mp3'])
    fake_mp3 = FakeMp3Player()
    deps = _makedeps(mp3player=fake_mp3, playlistdb=fake_db)
    dut = app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track1.mp3'

        dut.onButtonPressed(FakeButtons.NEXT)
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track2.mp3'

        dut.onButtonPressed(FakeButtons.NEXT)
        assert fake_mp3.track is None


def test_prev_plays_prev_track(micropythonify, faketimermanager, monkeypatch):
    fake_db = FakePlaylistDb([b'track1.mp3', b'track2.mp3'])
    fake_mp3 = FakeMp3Player()
    deps = _makedeps(mp3player=fake_mp3, playlistdb=fake_db)
    dut = app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track1.mp3'

        dut.onPlaybackDone()
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track2.mp3'

        dut.onButtonPressed(FakeButtons.PREV)
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track1.mp3'

        dut.onButtonPressed(FakeButtons.PREV)
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track1.mp3'


def test_pause_resume(micropythonify, faketimermanager, monkeypatch):
    fake_db = FakePlaylistDb([b'track1.mp3', b'track2.mp3'])
    fake_mp3 = FakeMp3Player()
    deps = _makedeps(mp3player=fake_mp3, playlistdb=fake_db)
    dut = app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track1.mp3'

        dut.onButtonPressed(FakeButtons.PLAY_PAUSE)
        assert fake_mp3.track is None

        dut.onButtonPressed(FakeButtons.PLAY_PAUSE)
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track1.mp3'


def test_pause_next_resumes(micropythonify, faketimermanager, monkeypatch):
    fake_db = FakePlaylistDb([b'track1.mp3', b'track2.mp3'])
    fake_mp3 = FakeMp3Player()
    deps = _makedeps(mp3player=fake_mp3, playlistdb=fake_db)
    dut = app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        FakeNfcReader.tag_callback.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track1.mp3'

        dut.onButtonPressed(FakeButtons.PLAY_PAUSE)
        assert fake_mp3.track is None

        dut.onButtonPressed(FakeButtons.NEXT)
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'track2.mp3'
