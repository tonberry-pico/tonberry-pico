// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2025 Matthias Blankertz <matthias@blankertz.org>

#include "audiocore.h"
#include "i2s.h"
#include "mp3.h"

#include "py/mperrno.h"

_Static_assert(MP3_FRAME_SIZE == I2S_DMA_BUF_SIZE, "i2s buffer size must match MP3 frame size");

void __time_critical_func(volume_adjust)(int16_t *buf, size_t samples, uint16_t scalef)
{
    for (size_t pos = 0; pos < samples; ++pos) {
        buf[pos] = ((int32_t)buf[pos] * scalef) >> 15;
    }
}

static void __time_critical_func(send_fifo_response)(uint32_t data)
{
    multicore_fifo_push_blocking(AUDIOCORE_FIFO_DATA_FLAG | data);
}

#ifndef UNIT_TESTING
static void __time_critical_func(send_consume_notify)(void)
{
    if (multicore_fifo_wready())
        sio_hw->fifo_wr = 0;
}
#else
// Don't do optimization with raw HW access in unit test environment
static void send_consume_notify(void)
{
    if (multicore_fifo_wready())
        multicore_fifo_push_blocking(0);
}
#endif

void __time_critical_func(core1_main)(void)
{
    uint32_t ret = 0;
    bool running = true, playing = false;
    if (!i2s_init(shared_context.out_pin, shared_context.sideset_base, shared_context.sideset_dclk_first)) {
        ret = MP_EIO;
        goto out;
    }
    if (!mp3_init()) {
        ret = MP_ENOMEM;
        goto out_i2s;
    }

    send_fifo_response(0);
    uint32_t current_volume = AUDIOCORE_MAX_VOLUME >> 4;
    bool flushing = false;
    while (running) {
        uint32_t cmd;
        uint32_t *buf;
        if (multicore_fifo_rvalid()) {
            cmd = multicore_fifo_pop_blocking();
            switch (cmd) {
            case AUDIOCORE_CMD_SHUTDOWN:
                running = false;
                break;
            case AUDIOCORE_CMD_SET_VOLUME: {
                const uint32_t new_volume = multicore_fifo_pop_blocking();
                if (new_volume > AUDIOCORE_MAX_VOLUME) {
                    send_fifo_response(1);
                } else {
                    current_volume = new_volume;
                    send_fifo_response(0);
                }
            } break;
            case AUDIOCORE_CMD_FLUSH:
                if (playing) {
                    flushing = true;
                } else {
                    send_fifo_response(0);
                }
                break;
            default:
                break;
            }
        }
        if ((buf = i2s_next_buf()) != NULL) {
            unsigned samplerate;
            // decode one frame
            if (mp3_decode(buf, &samplerate)) {
                if (!playing) {
                    i2s_play(samplerate);
                    playing = true;
                }
                volume_adjust((int16_t *)buf, MP3_FRAME_SIZE * 2, current_volume);
                i2s_commit_buf(buf);
                send_consume_notify();
                continue;
            }
            /* mp3_decode returned false: not enough data in buffer */
            if (flushing) {
                mp3_reset();
                i2s_stop();
                playing = false;
                flushing = false;
                send_fifo_response(0);
            } else {
                send_consume_notify();
            }
        }

        __wfe();
    }

    mp3_deinit();
out_i2s:
    i2s_deinit();
out:
    send_fifo_response(ret);
}
