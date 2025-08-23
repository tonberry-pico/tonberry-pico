# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import machine
from machine import Pin

# SD Card SPI
SD_DI = Pin.board.GP3
SD_DO = Pin.board.GP4
SD_SCK = Pin.board.GP2
SD_CS = Pin.board.GP5

# MAX98357
I2S_LRCLK = Pin.board.GP6
I2S_DCLK = Pin.board.GP7
I2S_DIN = Pin.board.GP8
I2S_SD = Pin.board.GP9

# RC522
RC522_SPIID = 1
RC522_RST = Pin.board.GP14
RC522_IRQ = Pin.board.GP15
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
BUTTON_POWER = Pin.board.GP21

# Power
POWER_EN = Pin.board.GP22
VBAT_ADC = Pin.board.GP26


def board_init():
    # Keep power turned on
    # TODO: Implement soft power off
    POWER_EN.init(mode=Pin.OUT)
    POWER_EN.value(1)

    # Set 8 mA drive strength and fast slew rate for SD SPI
    machine.mem32[0x4001c004 + 6*4] = 0x67
    machine.mem32[0x4001c004 + 7*4] = 0x67
    machine.mem32[0x4001c004 + 8*4] = 0x67

    # Permanently enable amplifier
    # TODO: Implement amplifier power management
    I2S_SD.init(mode=Pin.OPEN_DRAIN)
    I2S_SD.value(1)


def get_battery_voltage():
    adc = machine.ADC(VBAT_ADC)     # create ADC object on ADC pin
    battv = adc.read_u16()/65535.0*3.3*2
    return battv
