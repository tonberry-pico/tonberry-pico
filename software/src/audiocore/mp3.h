// SPDX-License-Identifier: MIT
// Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

#pragma once

#include <stdbool.h>
#include <stdint.h>

bool mp3_init(void);
void mp3_deinit(void);

bool mp3_decode(uint32_t pcm_buf[static 1152], unsigned *samplerate);

void mp3_reset(void);
