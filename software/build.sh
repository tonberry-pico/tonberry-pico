#!/usr/bin/bash

TOPDIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

set -eu

( cd lib/micropython
  make -C mpy-cross -j 16
  make -C ports/rp2 BOARD=TONBERRY_RPI_PICO_W BOARD_DIR=$TOPDIR/boards/RPI_PICO_W clean
  make -C ports/rp2 BOARD=TONBERRY_RPI_PICO_W BOARD_DIR=$TOPDIR/boards/RPI_PICO_W -j 16
)

echo "Output in lib/micropython/ports/rp2/build-TONBERRY_RPI_PICO_W/firmware.uf2"
