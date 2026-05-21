// SPDX-License-Identifier: MIT
// Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

#pragma once

#include <stdbool.h>
#include <stdint.h>

#define MP3_FRAME_SIZE 1152

bool mp3_init(void);
void mp3_deinit(void);

unsigned mp3_decode(uint32_t pcm_buf[static MP3_FRAME_SIZE], unsigned *samplerate);

void mp3_reset(void);
