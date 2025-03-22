// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2025 Matthias Blankertz <matthias@blankertz.org>

#pragma once

#include <stdbool.h>

struct spin_lock;
typedef struct spin_lock spin_lock_t;

void multicore_fifo_push_blocking(unsigned val);
unsigned multicore_fifo_pop_blocking(void);
bool multicore_fifo_rvalid(void);
bool multicore_fifo_wready(void);

#define __time_critical_func(x) x
#define __wfe()
