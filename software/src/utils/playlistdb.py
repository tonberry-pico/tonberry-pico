# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import btree
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

    class Playlist(IPlaylist):
        def __init__(self, parent, tag, pos, persist, shuffle):
            self.parent = parent
            self.tag = tag
            self.pos = pos
            self.persist = persist
            self.shuffle = shuffle

        def getPaths(self):
            """
            Get entire playlist in storage order
            """
            return self.parent._getPlaylistValueIterator(self.tag)

        def getCurrentPath(self):
            """
            Get path of file that should be played.
            """
            return self.parent._getPlaylistEntry(self.tag, self.pos)

        def getNextPath(self):
            """
            Select next track and return path.
            """
            try:
                self.pos = self.parent._getNextTrack(self.tag, self.pos)
            except StopIteration:
                self.pos = self.parent._getFirstTrack(self.tag)
                return None
            finally:
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

    def _getPlaylistValueIterator(self, tag):
        start, end = self._keyPlaylistStartEnd(tag)
        return self.db.values(start, end)

    def _getPlaylistEntry(self, _, pos):
        return self.db[pos]

    def _setPlaylistPos(self, tag, pos, flush=True):
        assert pos.startswith(self._keyPlaylistStart(tag))
        self.db[self._keyPlaylistPos(tag)] = pos[len(self._keyPlaylistStart(tag)):]
        if flush:
            self._flush()

    def _setPlaylistPosOffset(self, tag, offset, flush=True):
        self.db[self._keyPlaylistPosOffset(tag)] = str(offset).encode()
        if flush:
            self._flush()

    def _getPlaylistPosOffset(self, tag):
        return int(self.db.get(self._keyPlaylistPosOffset(tag), b'0'))

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
        try:
            del self.db[self._keyPlaylistPos(tag)]
        except KeyError:
            pass
        if flush:
            self._flush()

    def _getFirstTrack(self, tag: bytes):
        start_key, end_key = self._keyPlaylistStartEnd(tag)
        return next(self.db.keys(start_key, end_key))

    def _getNextTrack(self, tag, pos):
        _, end_key = self._keyPlaylistStartEnd(tag)
        it = self.db.keys(pos, end_key)
        next(it)
        return next(it)

    def getPlaylistForTag(self, tag: bytes):
        """
        Lookup the playlist for 'tag' and return the Playlist object. Return None if no playlist exists for the given
        tag.
        """
        persist = self.db.get(self._keyPlaylistPersist(tag), self.PERSIST_TRACK)
        if persist != self.PERSIST_NO:
            pos = self.db.get(self._keyPlaylistPos(tag))
        else:
            pos = None
        if pos is None:
            try:
                pos = self._getFirstTrack(tag)
            except StopIteration:
                # playist does not exist
                return None
        else:
            pos = self._keyPlaylistStart(tag) + pos
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
        index_width = None
        for k in self.db.keys():
            fields = k.split(b'/')
            if len(fields) <= 1:
                fail(f'Malformed key {k!r}')
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
                if index_width is not None and len(fields[2]) != index_width:
                    fail(f'Inconsistent index width for {last_tag} at {idx}')
                if (last_pos is not None and last_pos + 1 != idx) or \
                   (last_pos is None and idx != 0):
                    fail(f'Bad playlist entry sequence for {last_tag} at {idx}')
                last_pos = idx
                index_width = len(fields[2])
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
                if dump and val == 'yes':
                    print('\tShuffle')
            elif fields[1] == b'playlistpersist':
                val = self.db[k]
                if val not in (b'no', b'track', b'offset'):
                    fail(f'Bad playlistpersist value for {last_tag}: {val!r}')
                elif dump:
                    print(f'\tPersist: {val.decode()}')
            elif fields[1] == b'playlistshuffleseed':
                # Format TBD
                pass
            elif fields[1] == b'playlistposoffset':
                # Format TBD
                pass
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
