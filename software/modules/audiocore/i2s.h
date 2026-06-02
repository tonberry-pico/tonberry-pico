// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2025 Matthias Blankertz <matthias@blankertz.org>

#pragma once

#include <stdbool.h>
#include <stdint.h>

#define I2S_DMA_BUF_SIZE (1152)

bool i2s_init(int out_pin, int sideset_base, bool dclk_first);
void i2s_deinit(void);

void i2s_play(int samplerate);
void i2s_stop(void);

uint32_t *i2s_next_buf(void);
void i2s_commit_buf(uint32_t *buf, unsigned samples);
