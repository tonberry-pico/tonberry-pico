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

    def play(self, track: FakeFile):
        self.track = track


class FakeTimerManager:
    def __init__(self): pass
    def cancel(self, timer): pass


class FakeNfcReader:
    def __init__(self): pass


class FakeButtons:
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
                return None
            return self.parent.tracklist[self.pos]

    def __init__(self, tracklist=[b'test/path.mp3']):
        self.tracklist = tracklist

    def getPlaylistForTag(self, tag: bytes):
        return self.FakePlaylist(self)


def fake_open(filename, mode):
    return FakeFile(filename, mode)


@pytest.fixture
def faketimermanager(monkeypatch):
    monkeypatch.setattr(utils.timer.TimerManager, '_instance', FakeTimerManager())


def test_construct_app(micropythonify, faketimermanager):
    fake_mp3 = FakeMp3Player()
    deps = app.Dependencies(mp3player=lambda _: fake_mp3,
                            nfcreader=lambda _: FakeNfcReader(),
                            buttons=lambda _: FakeButtons(),
                            playlistdb=lambda _: FakePlaylistDb())
    _ = app.PlayerApp(deps)
    assert fake_mp3.volume is not None


def test_load_playlist_on_tag(micropythonify, faketimermanager, monkeypatch):
    fake_db = FakePlaylistDb()
    fake_mp3 = FakeMp3Player()
    deps = app.Dependencies(mp3player=lambda _: fake_mp3,
                            nfcreader=lambda _: FakeNfcReader(),
                            buttons=lambda _: FakeButtons(),
                            playlistdb=lambda _: fake_db)
    dut = app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        dut.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is not None
        assert fake_mp3.track.filename == b'test/path.mp3'
        assert "r" in fake_mp3.track.mode
        assert "b" in fake_mp3.track.mode


def test_playlist_seq(micropythonify, faketimermanager, monkeypatch):
    fake_db = FakePlaylistDb([b'track1.mp3', b'track2.mp3', b'track3.mp3'])
    fake_mp3 = FakeMp3Player()
    deps = app.Dependencies(mp3player=lambda _: fake_mp3,
                            nfcreader=lambda _: FakeNfcReader(),
                            buttons=lambda _: FakeButtons(),
                            playlistdb=lambda _: fake_db)
    dut = app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        dut.onTagChange([23, 42, 1, 2, 3])
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

    fake_db = FakeNoPlaylistDb()
    fake_mp3 = FakeMp3Player()
    deps = app.Dependencies(mp3player=lambda _: fake_mp3,
                            nfcreader=lambda _: FakeNfcReader(),
                            buttons=lambda _: FakeButtons(),
                            playlistdb=lambda _: fake_db)
    dut = app.PlayerApp(deps)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', fake_open)
        dut.onTagChange([23, 42, 1, 2, 3])
        assert fake_mp3.track is None
