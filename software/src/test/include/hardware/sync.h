// SPDX-License-Identifier: MIT
// Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

#pragma once

struct spin_lock;
typedef struct spin_lock spin_lock_t;

void multicore_fifo_push_blocking(unsigned val);
unsigned multicore_fifo_pop_blocking(void);
