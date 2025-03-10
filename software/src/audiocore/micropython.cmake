# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

add_subdirectory(${CMAKE_CURRENT_LIST_DIR}/../../lib/helix_mp3 helix_mp3)
add_library(usermod_audiocore INTERFACE)

pico_generate_pio_header(usermod_audiocore ${CMAKE_CURRENT_LIST_DIR}/i2s_max98357.pio)

target_sources(usermod_audiocore INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/audiocore.c
    ${CMAKE_CURRENT_LIST_DIR}/module.c
    ${CMAKE_CURRENT_LIST_DIR}/i2s.c
    ${CMAKE_CURRENT_BINARY_DIR}/i2s_max98357.pio.h
)

target_include_directories(usermod_audiocore INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod_audiocore INTERFACE helix_mp3)
target_link_libraries(usermod INTERFACE usermod_audiocore)
