#!/usr/bin/bash

TOPDIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

set -eu

( cd lib/micropython
  make -C mpy-cross -j "$(nproc)"
  make -C ports/rp2 BOARD=TONBERRY_RPI_PICO_W BOARD_DIR="$TOPDIR"/boards/RPI_PICO_W clean
  make -C ports/rp2 BOARD=TONBERRY_RPI_PICO_W BOARD_DIR="$TOPDIR"/boards/RPI_PICO_W \
       USER_C_MODULES="$TOPDIR"/src/micropython.cmake -j "$(nproc)"
)

( cd tools/mklittlefs
  make -j "$(nproc)"
)

PICOTOOL=picotool
if ! command -v $PICOTOOL >/dev/null 2>&1; then
    echo "system picotool not found, checking SDK build dir"
    PICOTOOL=lib/micropython/ports/rp2/build-TONBERRY_RPI_PICO_W/_deps/picotool-build/picotool
    if ! command -v $PICOTOOL >/dev/null 2>&1; then
       echo "No picotool found, exiting"
       exit 1
    fi
fi
BUILDDIR=lib/micropython/ports/rp2/build-TONBERRY_RPI_PICO_W/
tools/mklittlefs/mklittlefs -p 256 -s 868352 -c src/ $BUILDDIR/filesystem.bin
truncate -s 2M $BUILDDIR/firmware-filesystem.bin
dd if=$BUILDDIR/firmware.bin of=$BUILDDIR/firmware-filesystem.bin bs=1k
dd if=$BUILDDIR/filesystem.bin of=$BUILDDIR/firmware-filesystem.bin bs=1k seek=1200
$PICOTOOL uf2 convert $BUILDDIR/firmware-filesystem.bin $BUILDDIR/firmware-filesystem.uf2

echo "Output in $BUILDDIR/firmware.uf2"
echo "Image with filesystem in $BUILDDIR/firmware-filesystem.uf2"
