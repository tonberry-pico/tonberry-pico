// SPDX-License-Identifier: MIT
// Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

#pragma once

#include <hardware/sync.h>

#include <stdint.h>
#include <string.h>

/* Access rules
 * audiocore processing runs on core 1 and, unless stated otherwise, all
 * variables may only be accessed from core 1. Take care of interrupt safety
 * where needed. The micropython interface lives in module.c and is invoked from
 * the micropython runtime on core 0. Micropython objects may only be handled in
 * that context The audiocore_shared_context struct defined below is used for
 * communication between the cores.
 */

#define AUDIO_BUFFER_SIZE 2048

// Context shared between the micropython runtime on core0 and the audio task on
// core1 All access must hold "lock" unless otherwise noted
struct audiocore_shared_context {
    spin_lock_t *lock;

    // Set by module.c before core1 is launched and then never changed, can be read without lock
    int out_pin, sideset_base, samplerate;

    // Must hold lock
    uint32_t audio_buffer[AUDIO_BUFFER_SIZE];
    int audio_buffer_write, audio_buffer_read;
    int underruns;
};

extern struct audiocore_shared_context shared_context;

static inline unsigned audiocore_get_audio_buffer_space(void)
{
    if (shared_context.audio_buffer_write >= shared_context.audio_buffer_read)
        return AUDIO_BUFFER_SIZE - 1 - (shared_context.audio_buffer_write - shared_context.audio_buffer_read);
    else
        return shared_context.audio_buffer_read - shared_context.audio_buffer_write - 1;
}

static inline unsigned audiocore_get_audio_buffer_avail(void)
{
    if (shared_context.audio_buffer_write >= shared_context.audio_buffer_read)
        return shared_context.audio_buffer_write - shared_context.audio_buffer_read;
    else
        return AUDIO_BUFFER_SIZE - (shared_context.audio_buffer_read - shared_context.audio_buffer_write);
}

static inline void audiocore_audio_buffer_put(const uint32_t *restrict src, const size_t len)
{
    const unsigned end_samples = AUDIO_BUFFER_SIZE - shared_context.audio_buffer_write;
    memcpy(shared_context.audio_buffer + shared_context.audio_buffer_write, src,
           4 * ((end_samples >= len) ? len : end_samples));
    if (end_samples < len) {
        memcpy(shared_context.audio_buffer, src + end_samples, 4 * (len - end_samples));
        shared_context.audio_buffer_write = len - end_samples;
    } else {
        shared_context.audio_buffer_write += len;
    }
    shared_context.audio_buffer_write %= AUDIO_BUFFER_SIZE;
}

static inline void audiocore_audio_buffer_get(uint32_t *restrict dst, const size_t len)
{
    const unsigned end_samples = AUDIO_BUFFER_SIZE - shared_context.audio_buffer_read;
    memcpy(dst, shared_context.audio_buffer + shared_context.audio_buffer_read,
           4 * ((end_samples >= len) ? len : end_samples));
    if (end_samples < len) {
        memcpy(dst + end_samples, shared_context.audio_buffer, 4 * (len - end_samples));
        shared_context.audio_buffer_read = len - end_samples;
    } else {
        shared_context.audio_buffer_read += len;
    }
    shared_context.audio_buffer_read %= AUDIO_BUFFER_SIZE;
}

void core1_main(void);

// SHUTDOWN - no arguments - return 0
#define AUDIOCORE_CMD_SHUTDOWN 0xdeadc0de
