#!/bin/bash

DEVICEPATH=/dev/disk/by-label/RPI-RP2
IMAGEPATH=lib/micropython/ports/rp2/build-TONBERRY_RPI_PICO_W/firmware.uf2

flash_via_mountpoint()
{
    while [ ! -e "$DEVICEPATH" ] ; do sleep 1; echo 'Waiting for RP2...'; done
    
    set -eu
    
    while [ ! -e "$DEVICEPATH" ] ; do sleep 1; echo 'Waiting for RP2...'; done
    
    udisksctl mount -b "$DEVICEPATH"
    cp "$IMAGEPATH" "$(findmnt "$DEVICEPATH" -n -o TARGET)"
}

PID="2e8a"
VID="0003"

flash_via_picotool()
{
    while [ ! "$(lsusb -d $PID:$VID)" ] ; do sleep 1; echo 'Waiting for RP2 (USB)...'; done
    
    set -eu
    
    while [ ! "$(lsusb -d $PID:$VID)" ] ; do sleep 1; echo 'Waiting for RP2 (USB)...'; done

    local serial
    serial="$(lsusb -d $PID:$VID -v | grep "iSerial" | awk '{print $3}')"
    mapfile -t bus_device < <(lsusb -d 2e8a:0003 | awk '{print $2"\n"$4}')
    local bus="${bus_device[0]}"
    local device="${bus_device[1]//[!0-9]/}"
    echo "Found RP2 with serial $serial on Bus $bus Device $device"
    
    picotool load --bus "$bus" --address "$device" "$IMAGEPATH" 
}

FLASH_VIA_MOUNTPOINT=0

usage()
{
    echo "Usage: $0  [ -m | --via-mountpoint ]"
    echo
    echo "  -m, --via-mountpoint    Mount first found RP2 and flash image by"
    echo "                          copying to mountpoint."
    exit 2
}

PARSED_ARGUMENTS=$(getopt -a -n "$0" -o m --long via-mountpoint -- "$@")
# shellcheck disable=SC2181
# Indirect getopt return value checking is okay here
if [ "$?" != "0" ]; then
  usage
fi

eval set -- "$PARSED_ARGUMENTS"
while :
do
    case "$1" in
        -m | --via-mountpoint)   FLASH_VIA_MOUNTPOINT=1      ; shift   ;;
        --) shift; break ;;
        *) echo "Unexpected option: $1"
           usage ;;
    esac
done

if [ "$1" ]; then
    echo "Unexpected positional arguments: $1"
    usage
fi

if [ "$FLASH_VIA_MOUNTPOINT" -eq 0 ]; then
    flash_via_picotool
else
    flash_via_mountpoint
fi
