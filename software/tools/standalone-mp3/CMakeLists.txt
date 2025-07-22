cmake_minimum_required(VERSION 3.13)

# Workaround for pico-sdk host toolchain issue, see directory for details
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../../lib/micropython/ports/rp2/tools_patch")

# initialize pico-sdk from submodule
# note: this must happen before project()
include(../../lib/micropython/lib/pico-sdk/pico_sdk_init.cmake)

project(standalone_mp3)

option(ENABLE_WRITE_TEST "Enable write test" OFF)
option(ENABLE_PLAY_TEST "Enable mp3 playback test" OFF)
option(ENABLE_SD_READ_CRC "Enable crc check when reading from sd card" OFF)
option(ENABLE_SD_DEBUG "Enable debug output for sd card driver" OFF)

# initialize the Raspberry Pi Pico SDK
pico_sdk_init()

set(SD_LIB_DIR "${CMAKE_CURRENT_LIST_DIR}/../../modules/rp2_sd")

set(SD_LIB_SRCS
    "${SD_LIB_DIR}/sd.c"
    "${SD_LIB_DIR}/sd_spi.c"
)


add_executable(standalone_mp3
    main.c
    i2s.c
    ${CMAKE_CURRENT_BINARY_DIR}/sd_spi_pio.pio.h
    ${CMAKE_CURRENT_BINARY_DIR}/i2s_max98357.pio.h
    ${SD_LIB_SRCS}
)

if(ENABLE_WRITE_TEST)
    target_compile_definitions(standalone_mp3 PRIVATE WRITE_TEST)
endif()

if(ENABLE_PLAY_TEST)
    target_compile_definitions(standalone_mp3 PRIVATE PLAY_TEST)
endif()

if(ENABLE_SD_READ_CRC)
    target_compile_definitions(standalone_mp3 PRIVATE SD_READ_CRC_CHECK)
endif()

if(ENABLE_SD_DEBUG)
    target_compile_definitions(standalone_mp3 PRIVATE SD_DEBUG)
endif()

pico_generate_pio_header(standalone_mp3 ${SD_LIB_DIR}/sd_spi_pio.pio)

pico_generate_pio_header(standalone_mp3 ${CMAKE_CURRENT_LIST_DIR}/i2s_max98357.pio)

add_subdirectory(../../lib/helix_mp3 helix_mp3)

target_link_libraries(standalone_mp3 PRIVATE pico_stdlib hardware_dma hardware_spi hardware_sync hardware_pio helix_mp3)
target_include_directories(standalone_mp3 PRIVATE ${SD_LIB_DIR})
target_compile_options(standalone_mp3 PRIVATE -Og -DSD_DEBUG)


pico_add_extra_outputs(standalone_mp3)
pico_enable_stdio_uart(standalone_mp3 1)

set_property(TARGET standalone_mp3 APPEND_STRING PROPERTY LINK_FLAGS "-Wl,--print-memory-usage")

