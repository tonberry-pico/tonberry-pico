# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

from machine import Pin

# SD Card SPI
SD_DI = Pin.board.GP3
SD_DO = Pin.board.GP4
SD_SCK = Pin.board.GP2
SD_CS = Pin.board.GP5
SD_CLOCKRATE = 15000000

# MAX98357
I2S_LRCLK = Pin.board.GP7
I2S_DCLK = Pin.board.GP6
I2S_DIN = Pin.board.GP8
I2S_SD = None

# RC522
RC522_SPIID = 1
RC522_RST = Pin.board.GP9
RC522_IRQ = Pin.board.GP14
RC522_MOSI = Pin.board.GP11
RC522_MISO = Pin.board.GP12
RC522_SCK = Pin.board.GP10
RC522_SS = Pin.board.GP13

# WS2812
LED_DIN = Pin.board.GP16
LED_COUNT = 1

# Buttons
BUTTON_VOLUP = Pin.board.GP17
BUTTON_VOLDOWN = Pin.board.GP19
BUTTON_NEXT = Pin.board.GP18
BUTTON_POWER = None

# Power
POWER_EN = None
VBAT_ADC = Pin.board.GP26


def board_init():
    pass


def get_battery_voltage():
    # Not supported on breadboard
    return None
