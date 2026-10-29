# cmake file for Raspberry Pi Pico W

set(PICO_BOARD "pico_w")

# Flash filesystem partition size (mirrored in rp2_flash.c via a compile
# definition, and exposed to the linker as __micropy_flash_storage_bytes__ so
# memmap_rp2/memory_flash.incl can carve the FS partition out of FLASH).
if(NOT DEFINED MICROPY_HW_FLASH_STORAGE_BYTES)
    set(MICROPY_HW_FLASH_STORAGE_BYTES 868352)  # 848 * 1024
endif()

set(MICROPY_PY_LWIP ON)
set(MICROPY_PY_NETWORK_CYW43 ON)

# Bluetooth
set(MICROPY_PY_BLUETOOTH ON)
set(MICROPY_BLUETOOTH_BTSTACK ON)
set(MICROPY_PY_BLUETOOTH_CYW43 ON)

set(MICROPY_PY_BTREE ON)

# Board specific version of the frozen manifest
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)

set(GEN_PINS_BOARD_CSV "${CMAKE_CURRENT_LIST_DIR}/pins.csv")
set(GEN_PINS_CSV_ARG --board-csv "${GEN_PINS_BOARD_CSV}")

add_link_options("-Wl,--print-memory-usage")
set(PICO_USE_FASTEST_SUPPORTED_CLOCK 1)

find_program(GIT git)

execute_process(COMMAND ${GIT} rev-parse HEAD
    WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}"
    OUTPUT_VARIABLE TONBERRY_GIT_REVISION
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

execute_process(COMMAND ${GIT} describe --tags --match v\* --always --dirty
    WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}"
    OUTPUT_VARIABLE TONBERRY_VERSION
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

set(MICROPY_SOURCE_BOARD "${CMAKE_CURRENT_LIST_DIR}/board.c")
set(MICROPY_DEF_BOARD
    TONBERRY_GIT_REVISION="${TONBERRY_GIT_REVISION}"
    TONBERRY_VERSION="${TONBERRY_VERSION}")

# Linker script: using the new fragment approach introduced by the pico sdk.
# Setting MICROPY_BOARD_LINKER_SCRIPT here leads to micropython ignoring its
# own override paths (see lib/micropython/ports/rp2/CMakeLists.txt). The new
# fragment search path is here at memmap_tonberry/.
# It must be provided first so it can shadow fragments with the same (those are
# defined in the micropython). By adding memmap_rp2040/ and memmap_rp2/ the
# definitions from micropython are used as as fallbacks.
set(MICROPY_BOARD_LINKER_SCRIPT ${MICROPY_PORT_DIR}/memmap_mp_rp2.ld)
list(PREPEND PICO_LINKER_SCRIPT_INCLUDE_DIRS
    ${MICROPY_BOARD_DIR}/memmap_tonberry
    ${MICROPY_PORT_DIR}/memmap_rp2040
    ${MICROPY_PORT_DIR}/memmap_rp2
)
