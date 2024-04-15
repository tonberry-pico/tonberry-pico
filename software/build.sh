#!/usr/bin/bash

set -eu

( cd lib/micropython
  make -C mpy-cross -j 16
  make -C ports/rp2 BOARD=RPI_PICO_W clean
  make -C ports/rp2 BOARD=RPI_PICO_W -j 16
)

echo "Output in lib/micropython/ports/rp2/build-RPI_PICO_W/firmware.uf2"
