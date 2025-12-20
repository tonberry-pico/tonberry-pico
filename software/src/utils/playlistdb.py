# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import btree
import random
import time
try:
    import typing
    from typing import TYPE_CHECKING, Iterable  # type: ignore
except ImportError:
    TYPE_CHECKING = False
if TYPE_CHECKING:
    class IPlaylist(typing.Protocol):
        def getPaths(self) -> Iterable[bytes]: ...
        def getCurrentPath(self) -> bytes: ...
        def getNextPath(self) -> bytes | None: ...

    class IPlaylistDB(typing.Protocol):
        def getPlaylistForTag(self, tag: bytes) -> IPlaylist: ...
else:
    class IPlaylistDB(object):
        ...

    class IPlaylist(object):
        ...


class BTreeDB(IPlaylistDB):
    SHUFFLE_NO = b'no'
    SHUFFLE_YES = b'yes'
    PERSIST_NO = b'no'
    PERSIST_TRACK = b'track'
    PERSIST_OFFSET = b'offset'
    DEFAULT_SETTINGS = {
        b'tagmode': b'tagremains'
    }

    class Playlist(IPlaylist):
        def __init__(self, parent: "BTreeDB", tag: bytes, pos: int, persist, shuffle):
            self.parent = parent
            self.tag = tag
            self.pos = pos
            self.persist = persist
            self.shuffle = shuffle
            self.length = self.parent._getPlaylistLength(self.tag)
            self._shuffle()

        def _getPlaylistPos(self):
            """
            Gets the position to pass to parent._getPlaylistEntry etc.
            """
            if self.shuffle == BTreeDB.SHUFFLE_YES:
                return self.shuffle_order[self.pos]
            else:
                return self.pos

        def _shuffle(self, reshuffle=False):
            if self.shuffle == BTreeDB.SHUFFLE_NO:
                return

            self.shuffle_seed = None
            # Try to get seed from DB if persisted
            if self.persist != BTreeDB.PERSIST_NO and not reshuffle:
                self.shuffle_seed = self.parent._getPlaylistShuffleSeed(self.tag)
            if self.shuffle_seed is None:
                # Either not persisted or could not read from db
                self.shuffle_seed = time.ticks_cpu()
                if self.persist != BTreeDB.PERSIST_NO:
                    self.parent._setPlaylistShuffleSeed(self.tag, self.shuffle_seed)
            # TODO: Find an algorithm for shuffling that does not use O(n) memory for playlist of length n
            random.seed(self.shuffle_seed)
            entries = list(range(0, self.length))
            # We don't have random.shuffle in micropython, so emulate it with random.choice
            self.shuffle_order = []
            while len(entries) > 0:
                chosen = random.choice(entries)
                self.shuffle_order.append(chosen)
                entries.remove(chosen)

        def getPaths(self):
            """
            Get entire playlist in storage order
            """
            return self.parent._getPlaylistValueIterator(self.tag)

        def getCurrentPath(self):
            """
            Get path of file that should be played.
            """
            return self.parent._getPlaylistEntry(self.tag, self._getPlaylistPos())

        def getNextPath(self):
            """
            Select next track and return path.
            """
            if self.pos + 1 >= self.length:
                self.pos = 0
                if self.persist != BTreeDB.PERSIST_NO:
                    self.parent._setPlaylistPos(self.tag, self.pos)
                    self.setPlaybackOffset(0)
                    self._shuffle(True)
                return None

            self.pos += 1
            if self.persist != BTreeDB.PERSIST_NO:
                self.parent._setPlaylistPos(self.tag, self.pos)
                self.setPlaybackOffset(0)
            return self.getCurrentPath()

        def getPrevPath(self):
            """
            Select prev track and return path.
            """
            if self.pos > 0:
                self.pos -= 1
            if self.persist != BTreeDB.PERSIST_NO:
                self.parent._setPlaylistPos(self.tag, self.pos)
                self.setPlaybackOffset(0)
            return self.getCurrentPath()

        def setPlaybackOffset(self, offset):
            """
            Store the current position in the track for PERSIST_OFFSET mode
            """
            if self.persist != BTreeDB.PERSIST_OFFSET:
                return
            self.parent._setPlaylistPosOffset(self.tag, offset)

        def getPlaybackOffset(self):
            """
            Get the current position in the track for PERSIST_OFFSET mode
            """
            if self.persist != BTreeDB.PERSIST_OFFSET:
                return 0
            return self.parent._getPlaylistPosOffset(self.tag)

    def __init__(self, db: btree.BTree, flush_func: typing.Callable | None = None):
        self.db = db
        self.flush_func = flush_func

    @staticmethod
    def _keyPlaylistPos(tag):
        return b''.join([tag, b'/playlistpos'])

    @staticmethod
    def _keyPlaylistPosOffset(tag):
        return b''.join([tag, b'/playlistposoffset'])

    @staticmethod
    def _keyPlaylistShuffle(tag):
        return b''.join([tag, b'/playlistshuffle'])

    @staticmethod
    def _keyPlaylistShuffleSeed(tag):
        return b''.join([tag, b'/playlistshuffleseed'])

    @staticmethod
    def _keyPlaylistPersist(tag):
        return b''.join([tag, b'/playlistpersist'])

    @staticmethod
    def _keyPlaylistEntry(tag, pos):
        return b''.join([tag, b'/playlist/', '{:05}'.format(pos).encode()])

    @staticmethod
    def _keyPlaylistStart(tag):
        return b''.join([tag, b'/playlist/'])

    @staticmethod
    def _keyPlaylistStartEnd(tag):
        return (b''.join([tag, b'/playlist/']),
                b''.join([tag, b'/playlist0']))

    def _flush(self):
        """
        Flush the database and call the flush_func if it was provided.
        """
        self.db.flush()
        if self.flush_func is not None:
            self.flush_func()

    def _getPlaylistValueIterator(self, tag: bytes):
        start, end = self._keyPlaylistStartEnd(tag)
        return self.db.values(start, end)

    def _getPlaylistEntry(self, tag: bytes, pos: int) -> bytes:
        return self.db[self._keyPlaylistEntry(tag, pos)]

    def _setPlaylistPos(self, tag: bytes, pos: int, flush=True):
        self.db[self._keyPlaylistPos(tag)] = str(pos).encode()
        if flush:
            self._flush()

    def _setPlaylistPosOffset(self, tag: bytes, offset: int, flush=True):
        self.db[self._keyPlaylistPosOffset(tag)] = str(offset).encode()
        if flush:
            self._flush()

    def _getPlaylistPosOffset(self, tag: bytes) -> int:
        return int(self.db.get(self._keyPlaylistPosOffset(tag), b'0'))

    def _getPlaylistShuffleSeed(self, tag: bytes) -> int | None:
        try:
            return int(self.db[self._keyPlaylistShuffleSeed(tag)])
        except (ValueError, KeyError):
            return None

    def _setPlaylistShuffleSeed(self, tag, seed: int, flush=True):
        self.db[self._keyPlaylistShuffleSeed(tag)] = str(seed).encode()
        if flush:
            self._flush()

    def _getPlaylistLength(self, tag: bytes) -> int:
        start, end = self._keyPlaylistStartEnd(tag)
        for k in self.db.keys(end, start, btree.DESC):
            # There is a bug in btreedb that causes an additional key after 'end' to be returned when iterating in
            # descending order
            # Check for this and skip it if needed
            elements = k.split(b'/')
            if len(elements) >= 2 and elements[1] == b'playlist':
                last = k
                break
        elements = last.split(b'/')
        if len(elements) != 3:
            raise RuntimeError("Malformed playlist key")
        return int(elements[2])+1

    def _savePlaylist(self, tag, entries, persist, shuffle, flush=True):
        self._deletePlaylist(tag, False)
        for idx, entry in enumerate(entries):
            self.db[self._keyPlaylistEntry(tag, idx)] = entry
        self.db[self._keyPlaylistPersist(tag)] = persist
        self.db[self._keyPlaylistShuffle(tag)] = shuffle
        if flush:
            self._flush()

    def _deletePlaylist(self, tag, flush=True):
        start_key, end_key = self._keyPlaylistStartEnd(tag)
        for k in self.db.keys(start_key, end_key):
            try:
                del self.db[k]
            except KeyError:
                pass
        for k in (self._keyPlaylistPos(tag), self._keyPlaylistPosOffset(tag),
                  self._keyPlaylistPersist(tag), self._keyPlaylistShuffle(tag),
                  self._keyPlaylistShuffleSeed(tag)):
            try:
                del self.db[k]
            except KeyError:
                pass
        if flush:
            self._flush()

    def getPlaylistTags(self):
        """
        Get a keys-only dict of all defined playlists. Playlists currently do not have names, but are identified by
        their tag.
        """
        playlist_tags = set()
        for item in self.db:
            playlist_tags.add(item.split(b'/')[0])
        return playlist_tags

    def getPlaylistForTag(self, tag: bytes):
        """
        Lookup the playlist for 'tag' and return the Playlist object. Return None if no playlist exists for the given
        tag.
        """
        persist = self.db.get(self._keyPlaylistPersist(tag), self.PERSIST_TRACK)
        pos = 0
        if persist != self.PERSIST_NO and self._keyPlaylistPos(tag) in self.db:
            try:
                pos = int(self.db[self._keyPlaylistPos(tag)])
            except ValueError:
                pass
        if self._keyPlaylistEntry(tag, 0) not in self.db:
            # Empty playlist
            return None
        if self._keyPlaylistEntry(tag, pos) not in self.db:
            pos = 0
        shuffle = self.db.get(self._keyPlaylistShuffle(tag), self.SHUFFLE_NO)
        return self.Playlist(self, tag, pos, persist, shuffle)

    def createPlaylistForTag(self, tag: bytes, entries: typing.Iterable[bytes], persist=PERSIST_TRACK,
                             shuffle=SHUFFLE_NO):
        """
        Create and save a playlist for 'tag' and return the Playlist object. If a playlist already existed for 'tag' it
        is overwritten.
        """
        assert persist in (self.PERSIST_NO, self.PERSIST_TRACK, self.PERSIST_OFFSET)
        assert shuffle in (self.SHUFFLE_NO, self.SHUFFLE_YES)
        self._savePlaylist(tag, entries, persist, shuffle)
        return self.getPlaylistForTag(tag)

    def getSetting(self, key: bytes | str) -> str:
        if type(key) is str:
            key = key.encode()
        return self.db.get(b'settings/' + key, self.DEFAULT_SETTINGS[key]).decode()

    def deletePlaylistForTag(self, tag: bytes):
        self._deletePlaylist(tag)

    def validate(self, dump=False):
        """
        Validate the structure of the playlist database.
        """
        result = True

        def fail(msg):
            nonlocal result
            print(msg)
            result = False

        last_tag = None
        last_pos = None
        for k in self.db.keys():
            fields = k.split(b'/')
            if len(fields) <= 1:
                fail(f'Malformed key {k!r}')
                continue
            if fields[0] == b'settings':
                val = self.db[k].decode()
                print(f'Setting {fields[1].decode()} = {val}')
                continue
            if last_tag != fields[0]:
                last_tag = fields[0]
                last_pos = None
                if dump:
                    print(f'Tag {fields[0]}')
            if fields[1] == b'playlist':
                if len(fields) != 3:
                    fail(f'Malformed playlist entry: {k!r}')
                    continue
                try:
                    idx = int(fields[2])
                except ValueError:
                    fail(f'Malformed playlist entry: {k!r}')
                    continue
                if len(fields[2]) != 5:
                    fail(f'Bad index width for {last_tag} at {idx}')
                if (last_pos is not None and last_pos + 1 != idx) or \
                   (last_pos is None and idx != 0):
                    fail(f'Bad playlist entry sequence for {last_tag} at {idx}')
                last_pos = idx
                if dump:
                    print(f'\tTrack {idx}: {self.db[k]!r}')
            elif fields[1] == b'playlistpos':
                val = self.db[k]
                try:
                    idx = int(val)
                except ValueError:
                    fail(f'Malformed playlist position: {val!r}')
                    continue
                if 0 > idx or idx > last_pos:
                    fail(f'Playlist position out of range for {last_tag}: {idx}')
                elif dump:
                    print(f'\tPosition {idx}')
            elif fields[1] == b'playlistshuffle':
                val = self.db[k]
                if val not in (b'no', b'yes'):
                    fail(f'Bad playlistshuffle value for {last_tag}: {val!r}')
                if dump and val == b'yes':
                    print('\tShuffle')
            elif fields[1] == b'playlistpersist':
                val = self.db[k]
                if val not in (b'no', b'track', b'offset'):
                    fail(f'Bad playlistpersist value for {last_tag}: {val!r}')
                elif dump:
                    print(f'\tPersist: {val.decode()}')
            elif fields[1] == b'playlistshuffleseed':
                val = self.db[k]
                try:
                    _ = int(val)
                except ValueError:
                    fail(f' Bad playlistshuffleseed value for {last_tag}: {val!r}')
            elif fields[1] == b'playlistposoffset':
                val = self.db[k]
                try:
                    _ = int(val)
                except ValueError:
                    fail(f' Bad playlistposoffset value for {last_tag}: {val!r}')
            else:
                fail(f'Unknown key {k!r}')
        return result


class BTreeFileManager:
    """
    Context manager for a BTreeDB playlist db backed by a file in the filesystem.
    """
    def __init__(self, db_path: str | bytes):
        self.db_path = db_path

    def __enter__(self):
        try:
            self.db_file = open(self.db_path, 'r+b')
        except OSError:
            self.db_file = open(self.db_path, 'w+b')
        try:
            self.db = btree.open(self.db_file, pagesize=512, cachesize=1024)
            btdb = BTreeDB(self.db, lambda: self.db_file.flush())
            btdb.validate(True)  # while testing, validate and dump DB on startup
            return btdb
        except Exception:
            self.db_file.close()
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        self.db.close()
        self.db_file.close()
