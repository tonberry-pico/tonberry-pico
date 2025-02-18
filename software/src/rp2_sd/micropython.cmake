# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

add_library(usermod_rp2_sd INTERFACE)

pico_generate_pio_header(usermod_rp2_sd ${CMAKE_CURRENT_LIST_DIR}/sd_spi_pio.pio)

target_sources(usermod_rp2_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/module.c
    ${CMAKE_CURRENT_LIST_DIR}/sd.c
    ${CMAKE_CURRENT_LIST_DIR}/sd_spi.c
    ${CMAKE_CURRENT_BINARY_DIR}/sd_spi_pio.pio.h
)

target_include_directories(usermod_rp2_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_rp2_sd)
