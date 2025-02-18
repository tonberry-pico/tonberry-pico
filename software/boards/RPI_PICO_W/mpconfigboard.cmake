# cmake file for Raspberry Pi Pico W

set(PICO_BOARD "pico_w")

set(MICROPY_PY_LWIP ON)
set(MICROPY_PY_NETWORK_CYW43 ON)

# Bluetooth
set(MICROPY_PY_BLUETOOTH ON)
set(MICROPY_BLUETOOTH_BTSTACK ON)
set(MICROPY_PY_BLUETOOTH_CYW43 ON)

# Board specific version of the frozen manifest
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)

set(GEN_PINS_BOARD_CSV "${CMAKE_CURRENT_LIST_DIR}/pins.csv")
set(GEN_PINS_CSV_ARG --board-csv "${GEN_PINS_BOARD_CSV}")

add_link_options("-Wl,--print-memory-usage")
