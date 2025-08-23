# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

from typing import Iterable


class BTree:
    def close(self): ...

    def values(self, start_key: str | bytes, end_key: str | bytes | None = None, flags=None) -> Iterable[str | bytes]:
        pass

    def __setitem__(self, key: str | bytes, val: str | bytes): ...

    def flush(self): ...

    def get(self, key: str | bytes, default: str | bytes | None = None) -> str | bytes: ...


def open(dbfile) -> BTree:
    pass
