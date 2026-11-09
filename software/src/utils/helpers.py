# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import sys


def safe_callback(func, logger, name="callback"):
    try:
        func()
    except Exception as ex:
        logger.error("Uncaught exception in %s", name)
        sys.print_exception(ex)
