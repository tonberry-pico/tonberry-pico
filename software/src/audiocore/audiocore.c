// SPDX-License-Identifier: MIT
// Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

#include "audiocore.h"
#include "i2s.h"

#include "py/mperrno.h"

void core1_main(void)
{
    if (!i2s_init(shared_context.out_pin, shared_context.sideset_base, shared_context.samplerate)) {
        multicore_fifo_push_blocking(MP_EIO);
        return;
    }

    multicore_fifo_push_blocking(0);
    uint32_t cmd;
    while ((cmd = multicore_fifo_pop_blocking()) != AUDIOCORE_CMD_SHUTDOWN) {
        switch (cmd) {
        default:
            break;
        }
    }

    i2s_deinit();
    multicore_fifo_push_blocking(0);
}
