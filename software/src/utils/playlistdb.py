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
    class Playlist(IPlaylist):
        def __init__(self, parent, tag, pos):
            self.parent = parent
            self.tag = tag
            self.pos = pos

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
                self.parent._setPlaylistPos(self.tag, self.pos)
            return self.getCurrentPath()

    def __init__(self, db: btree.BTree, flush_func: typing.Callable | None = None):
        self.db = db
        self.flush_func = flush_func

    @staticmethod
    def _keyPlaylistPos(tag):
        return b''.join([tag, b'/playlistpos'])

    @staticmethod
    def _keyPlaylistEntry(tag, pos):
        return b''.join([tag, b'/playlist/', "{:03}".format(pos).encode()])

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
        self.db[self._keyPlaylistPos(tag)] = pos.removeprefix(self._keyPlaylistStart(tag))
        if flush:
            self._flush()

    def _savePlaylist(self, tag, entries, flush=True):
        self._deletePlaylist(tag, False)
        for idx, entry in enumerate(entries):
            self.db[self._keyPlaylistEntry(tag, idx)] = entry
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
        pos = self.db.get(self._keyPlaylistPos(tag))
        if pos is None:
            try:
                pos = self._getFirstTrack(tag)
            except StopIteration:
                # playist does not exist
                return None
        else:
            pos = self._keyPlaylistStart(tag) + pos
        return self.Playlist(self, tag, pos)

    def createPlaylistForTag(self, tag: bytes, entries: typing.Iterable[bytes]):
        """
        Create and save a playlist for 'tag' and return the Playlist object. If a playlist already existed for 'tag' it
        is overwritten.
        """
        self._savePlaylist(tag, entries)
        return self.getPlaylistForTag(tag)


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
            return BTreeDB(self.db, lambda: self.db_file.flush())
        except Exception:
            self.db_file.close()
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        self.db.close()
        self.db_file.close()
