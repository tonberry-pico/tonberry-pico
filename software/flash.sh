#!/bin/bash

DEVICEPATH=/dev/disk/by-label/RPI-RP2
IMAGEPATH=lib/micropython/ports/rp2/build-TONBERRY_RPI_PICO_W/firmware.uf2

while [ ! -e "$DEVICEPATH" ] ; do sleep 1; echo 'Waiting for RP2...'; done

set -eu

udisksctl mount -b "$DEVICEPATH"
cp "$IMAGEPATH" "$(findmnt "$DEVICEPATH" -n -o TARGET)"
