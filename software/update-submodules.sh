#!/usr/bin/bash

set -eu

git submodule update --init lib
git -C lib/micropython submodule update --init \
    lib/pico-sdk lib/mbedtls lib/micropython-lib lib/tinyusb lib/btstack lib/cyw43-driver lib/lwip \
    lib/berkeley-db-1.xx
git -C lib/micropython/lib/pico-sdk submodule update --init lib
git submodule update --init --recursive tools/mklittlefs
