# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

make_unity_test(NAME test_audiocore
    TEST_SOURCE test/test_audiocore.c
    SOURCES audiocore.c
    INCLUDES "${CMAKE_CURRENT_SOURCE_DIR}/../test/include" "${CMAKE_CURRENT_SOURCE_DIR}"
)
