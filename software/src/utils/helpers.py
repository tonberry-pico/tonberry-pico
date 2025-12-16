# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import sys


def safe_callback(func, name="callback"):
    try:
        func()
    except Exception as ex:
        print(f"Uncaught exception in {name}")
        sys.print_exception(ex)
