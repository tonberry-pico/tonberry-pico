// SPDX-License-Identifier: MIT
// Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

#pragma once

#include <stdbool.h>

bool i2s_init(int out_pin, int sideset_base, int samplerate);

void i2s_deinit(void);
