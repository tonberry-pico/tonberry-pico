#!/usr/bin/bash

TOPDIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

set -eu

( cd lib/micropython
  make -C mpy-cross -j "$(nproc)"
  make -C ports/rp2 BOARD=TONBERRY_RPI_PICO_W BOARD_DIR="$TOPDIR"/boards/RPI_PICO_W clean
  make -C ports/rp2 BOARD=TONBERRY_RPI_PICO_W BOARD_DIR="$TOPDIR"/boards/RPI_PICO_W \
       USER_C_MODULES="$TOPDIR"/modules/micropython.cmake -j "$(nproc)"

  # build tonberry specific unix port of micropython
  make -C ports/unix VARIANT_DIR="$TOPDIR"/boards/tonberry_unix clean
  make -C ports/unix VARIANT_DIR="$TOPDIR"/boards/tonberry_unix -j "$(nproc)"
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
FS_STAGE_DIR=$(mktemp -d)
trap 'rm -rf $FS_STAGE_DIR' EXIT
for hwconfig in src/hwconfig_*.py; do
    hwconfig_base=$(basename "$hwconfig")
    hwname=${hwconfig_base##hwconfig_}
    hwname=${hwname%%.py}
    find src/ -iname '*.py' \! -iname 'hwconfig_*.py' | cpio -pdm "$FS_STAGE_DIR"
    cp "$hwconfig" "$FS_STAGE_DIR"/src/hwconfig.py
    tools/mklittlefs/mklittlefs -p 256 -s 868352 -c "$FS_STAGE_DIR"/src $BUILDDIR/filesystem.bin
    truncate -s 2M $BUILDDIR/firmware-filesystem.bin
    dd if=$BUILDDIR/firmware.bin of=$BUILDDIR/firmware-filesystem.bin bs=1k
    dd if=$BUILDDIR/filesystem.bin of=$BUILDDIR/firmware-filesystem.bin bs=1k seek=1200
    $PICOTOOL uf2 convert $BUILDDIR/firmware-filesystem.bin $BUILDDIR/firmware-filesystem-"$hwname".uf2
    rm -r "${FS_STAGE_DIR:?}"/*
done

echo "Output in $BUILDDIR/firmware.uf2"
echo "Images with filesystem in" ${BUILDDIR}firmware-filesystem-*.uf2
