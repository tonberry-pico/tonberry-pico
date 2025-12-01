# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import machine
from machine import Pin

# SD Card SPI
SD_DI = Pin.board.GP3
SD_DO = Pin.board.GP4
SD_SCK = Pin.board.GP2
SD_CS = Pin.board.GP5
SD_CLOCKRATE = 25000000

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
VBUS_DET = Pin.board.WL_GPIO2


def board_init():
    # POWER_EN turned on in MICROPY_BOARD_STARTUP
    # TODO: Implement soft power off

    # SD_DO / MISO input doesn't need any special configuration
    # Set 8 mA drive strength for SCK and MOSI
    machine.mem32[0x4001c004 + 2*4] = 0x60  # SCK
    machine.mem32[0x4001c004 + 3*4] = 0x60  # MOSI
    # SD_CS doesn't need any special configuration

    # Permanently enable amplifier
    # TODO: Implement amplifier power management
    I2S_SD.init(mode=Pin.OPEN_DRAIN)
    I2S_SD.value(1)


def get_battery_voltage():
    adc = machine.ADC(VBAT_ADC)     # create ADC object on ADC pin
    battv = adc.read_u16()/65535.0*3.3*2
    return battv


def power_off():
    POWER_EN.init(mode=Pin.OUT)
    POWER_EN.value(0)


def get_on_battery():
    vbus = VBUS_DET.value()
    return not vbus
