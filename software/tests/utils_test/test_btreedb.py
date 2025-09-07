# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import btree
import pytest
import time
from utils import BTreeDB


@pytest.fixture(autouse=True)
def micropythonify():
    def time_ticks_cpu():
        return time.time_ns()
    time.ticks_cpu = time_ticks_cpu
    yield
    del time.ticks_cpu


class FakeDB:
    def __init__(self, contents):
        self.contents = contents
        self.saved_contents = dict(contents)

    def flush(self):
        self.saved_contents = dict(self.contents)

    def values(self, start_key=None, end_key=None, flags=None):
        res = []
        for key in sorted(self.contents):
            if start_key is not None and start_key > key:
                continue
            if end_key is not None and end_key <= key:
                break
            yield self.contents[key]
            res.append(self.contents[key])

    def keys(self, start_key=None, end_key=None, flags=None):
        keys = []
        if flags is not None and flags & btree.DESC != 0:
            start_key, end_key = end_key, start_key
        for key in sorted(self.contents):
            if start_key is not None and start_key > key:
                continue
            if end_key is not None and end_key <= key:
                break
            keys.append(key)
        if flags is not None and flags & btree.DESC != 0:
            keys.reverse()
        return iter(keys)

    def get(self, key, default=None):
        return self.contents.get(key, default)

    def __getitem__(self, key):
        return self.contents[key]

    def __setitem__(self, key, val):
        self.contents[key] = val

    def __delitem__(self, key):
        del self.contents[key]

    def __contains__(self, key):
        return key in self.contents


def test_playlist_load():
    contents = {b'foo/part': b'no',
                b'foo/playlist/00000': b'track1',
                b'foo/playlist/00001': b'track2',
                b'foo/playlisttt': b'no'
                }
    uut = BTreeDB(FakeDB(contents))
    pl = uut.getPlaylistForTag(b'foo')
    assert list(pl.getPaths()) == [b'track1', b'track2']
    assert pl.getCurrentPath() == b'track1'


def test_playlist_nextpath():
    contents = FakeDB({b'foo/part': b'no',
                       b'foo/playlist/00000': b'track1',
                       b'foo/playlist/00001': b'track2',
                       b'foo/playlisttt': b'no'
                       })
    uut = BTreeDB(contents)
    pl = uut.getPlaylistForTag(b'foo')
    assert pl.getNextPath() == b'track2'
    assert contents.saved_contents[b'foo/playlistpos'] == b'1'


def test_playlist_nextpath_last():
    contents = FakeDB({b'foo/playlist/00000': b'track1',
                       b'foo/playlist/00001': b'track2',
                       b'foo/playlistpos': b'1'
                       })
    uut = BTreeDB(contents)
    pl = uut.getPlaylistForTag(b'foo')
    assert pl.getNextPath() is None
    assert contents.saved_contents[b'foo/playlistpos'] == b'0'


def test_playlist_create():
    contents = FakeDB({b'foo/playlist/00000': b'track1',
                       b'foo/playlist/00001': b'track2',
                       b'foo/playlistpos': b'1'
                       })
    newplaylist = [b'never gonna give you up.mp3', b'durch den monsun.mp3']
    uut = BTreeDB(contents)
    new_pl = uut.createPlaylistForTag(b'foo', newplaylist)
    assert list(new_pl.getPaths()) == newplaylist
    assert new_pl.getCurrentPath() == newplaylist[0]
    assert uut.validate(True)


def test_playlist_load_notexist():
    contents = FakeDB({b'foo/playlist/00000': b'track1',
                       b'foo/playlist/00001': b'track2',
                       b'foo/playlistpos': b'1'
                       })
    uut = BTreeDB(contents)
    assert uut.getPlaylistForTag(b'notfound') is None


def test_playlist_starts_at_beginning_in_persist_no_mode():
    contents = FakeDB({b'foo/playlist/00000': b'track1',
                       b'foo/playlist/00001': b'track2',
                       b'foo/playlistpersist': b'no',
                       })
    uut = BTreeDB(contents)
    pl = uut.getPlaylistForTag(b'foo')
    assert pl.getCurrentPath() == b'track1'
    assert pl.getNextPath() == b'track2'
    del pl
    pl = uut.getPlaylistForTag(b'foo')
    assert pl.getCurrentPath() == b'track1'


@pytest.mark.parametrize("mode", [b'no', b'track'])
def test_playlist_ignores_offset_in_other_modes(mode):
    contents = FakeDB({b'foo/playlist/00000': b'track1',
                       b'foo/playlist/00001': b'track2',
                       b'foo/playlistpersist': mode,
                       })
    uut = BTreeDB(contents)
    pl = uut.getPlaylistForTag(b'foo')
    pl.setPlaybackOffset(42)
    del pl
    pl = uut.getPlaylistForTag(b'foo')
    assert pl.getPlaybackOffset() == 0


def test_playlist_stores_offset_in_offset_mode():
    contents = FakeDB({b'foo/playlist/00000': b'track1',
                       b'foo/playlist/00001': b'track2',
                       b'foo/playlistpersist': b'offset',
                       })
    uut = BTreeDB(contents)
    pl = uut.getPlaylistForTag(b'foo')
    pl.setPlaybackOffset(42)
    del pl
    pl = uut.getPlaylistForTag(b'foo')
    assert pl.getPlaybackOffset() == 42


def test_playlist_resets_offset_on_next_track():
    contents = FakeDB({b'foo/playlist/00000': b'track1',
                       b'foo/playlist/00001': b'track2',
                       b'foo/playlistpersist': b'offset',
                       })
    uut = BTreeDB(contents)
    pl = uut.getPlaylistForTag(b'foo')
    pl.setPlaybackOffset(42)
    assert pl.getNextPath() == b'track2'
    del pl
    pl = uut.getPlaylistForTag(b'foo')
    assert pl.getCurrentPath() == b'track2'
    assert pl.getPlaybackOffset() == 0


def test_playlist_shuffle():
    contents_dict = {b'foo/playlistpersist': b'track',
                     b'foo/playlistshuffle': b'yes',
                     }
    for i in range(256):
        contents_dict['foo/playlist/{:05}'.format(i).encode()] = 'track{}'.format(i).encode()
    contents = FakeDB(contents_dict)
    uut = BTreeDB(contents)
    pl = uut.getPlaylistForTag(b'foo')
    shuffled = False
    last_idx = int(pl.getCurrentPath().removeprefix(b'track'))
    while (t := pl.getNextPath()) is not None:
        idx = int(t.removeprefix(b'track'))
        if idx != last_idx + 1:
            shuffled = True
            break
    # A false negative ratr of 1 in 256! should be good enough for this test
    assert shuffled
