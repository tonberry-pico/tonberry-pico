#!/usr/bin/bash

TOPDIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

set -eu

echo "GIT version" "$(git describe --tags --match v\* --always --dirty)"
git show-ref --tags

( cd lib/micropython
  make -C mpy-cross -j "$(nproc)"

  # build tonberry specific unix port of micropython
  make -C ports/unix VARIANT_DIR="$TOPDIR"/boards/tonberry_unix clean
  make -C ports/unix VARIANT_DIR="$TOPDIR"/boards/tonberry_unix -j "$(nproc)"
)

( cd tools/mklittlefs
  make -j "$(nproc)"
)

BUILDDIR=lib/micropython/ports/rp2/build-TONBERRY_RPI_PICO_W/
BUILDDIR_UNIX=lib/micropython/ports/unix/build-tonberry_unix/
OUTDIR=$(pwd)/build
mkdir -p "$OUTDIR"
FS_STAGE_DIR=$(mktemp -d)
mkdir  "$FS_STAGE_DIR"/fs
trap 'rm -rf $FS_STAGE_DIR' EXIT
tools/mklittlefs/mklittlefs -p 256 -s 868352 -c "$FS_STAGE_DIR"/fs "$FS_STAGE_DIR"/filesystem.bin

FRONTEND_STAGE_DIR=$(mktemp -d)
trap 'rm -rf $FRONTEND_STAGE_DIR' EXIT
gzip -c frontend/index.html > "$FRONTEND_STAGE_DIR"/index.html.gz
python -m freezefs "$FRONTEND_STAGE_DIR" build/frozen_frontend.py --target=/frontend

for hwconfig in boards/RPI_PICO_W/manifest-*.py; do
    hwconfig_base=$(basename "$hwconfig")
    hwname=${hwconfig_base##manifest-}
    hwname=${hwname%%.py}
    hwconfig_abs=$(realpath "$hwconfig")
    ( cd lib/micropython
      make -C ports/rp2 BOARD=TONBERRY_RPI_PICO_W BOARD_DIR="$TOPDIR"/boards/RPI_PICO_W clean
      make -C ports/rp2 BOARD=TONBERRY_RPI_PICO_W BOARD_DIR="$TOPDIR"/boards/RPI_PICO_W \
           USER_C_MODULES="$TOPDIR"/modules/micropython.cmake \
           FROZEN_MANIFEST="$hwconfig_abs" -j "$(nproc)"
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
    truncate -s 2M $BUILDDIR/firmware-filesystem.bin
    dd if=$BUILDDIR/firmware.bin of=$BUILDDIR/firmware-filesystem.bin bs=1k
    dd if="$FS_STAGE_DIR"/filesystem.bin of=$BUILDDIR/firmware-filesystem.bin bs=1k seek=1200
    cp $BUILDDIR/firmware.uf2 "$OUTDIR"/firmware-"$hwname".uf2
    $PICOTOOL uf2 convert $BUILDDIR/firmware-filesystem.bin "$OUTDIR"/firmware-filesystem-"$hwname".uf2
done

cp "$BUILDDIR_UNIX"/micropython "$OUTDIR"/micropython-tonberry_unix
chmod u+x "$OUTDIR"/micropython-tonberry_unix

echo "Output in" "${OUTDIR}"/firmware-*.uf2
echo "Images with filesystem in" "${OUTDIR}"/firmware-filesystem-*.uf2
echo "Unix build in" "${OUTDIR}"/micropython-tonberry_unix
