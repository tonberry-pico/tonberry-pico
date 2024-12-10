#!/usr/bin/bash

TOPDIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

set -eu

( cd lib/micropython
  make -C mpy-cross -j "$(nproc)"
  make -C ports/rp2 BOARD=TONBERRY_RPI_PICO_W BOARD_DIR="$TOPDIR"/boards/RPI_PICO_W clean
  make -C ports/rp2 BOARD=TONBERRY_RPI_PICO_W BOARD_DIR="$TOPDIR"/boards/RPI_PICO_W \
       USER_C_MODULES="$TOPDIR"/src/audiocore/micropython.cmake -j "$(nproc)"
)

echo "Output in lib/micropython/ports/rp2/build-TONBERRY_RPI_PICO_W/firmware.uf2"
