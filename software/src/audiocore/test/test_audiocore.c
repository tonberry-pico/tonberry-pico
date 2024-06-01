// SPDX-License-Identifier: MIT
// Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

#include "audiocore.h"
#include "i2s.h"

#include "unity.h"

struct audiocore_shared_context shared_context;

bool i2s_init(int out_pin, int sideset_base, int samplerate) {}

void i2s_deinit(void) {}

void multicore_fifo_push_blocking(unsigned val) {}

unsigned multicore_fifo_pop_blocking(void) {}

void test_something(void) { TEST_ASSERT_TRUE(1); }
