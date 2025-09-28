// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2025 Matthias Blankertz <matthias@blankertz.org>

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

#define MP3_BUFFER_ALIGN (sizeof(uintptr_t))
#define MP3_BUFFER_SIZE 4096
#define MP3_BUFFER_PREAREA 1048

_Static_assert(MP3_BUFFER_PREAREA % MP3_BUFFER_ALIGN == 0,
               "Prearea must be a multiple of machine word size for alignment");

// Context shared between the micropython runtime on core0 and the audio task on
// core1 All access must hold "lock" unless otherwise noted
struct audiocore_shared_context {
    spin_lock_t *lock;

    // Set by module.c before core1 is launched and then never changed, can be read without lock
    int out_pin, sideset_base, samplerate;
    bool sideset_dclk_first;

    // Must hold lock. The indices 0..MP3_BUFFER_PREAREA-1 may only be read and written on core1 (no
    // lock needed) The buffer is aligned to, and MP3_BUFFER_PREAREA is a multiple of, the machine
    // word size to prevent these accesses from crossing word boundaries.
    char mp3_buffer[MP3_BUFFER_PREAREA + MP3_BUFFER_SIZE] __attribute__((aligned(MP3_BUFFER_ALIGN)));
    int mp3_buffer_write, mp3_buffer_read;
    int underruns;
};

extern struct audiocore_shared_context shared_context;

/* Must hold audiocore_shared_context.lock */
static inline unsigned audiocore_get_buffer_space(void)
{
    if (shared_context.mp3_buffer_write >= shared_context.mp3_buffer_read)
        return MP3_BUFFER_SIZE - 1 - (shared_context.mp3_buffer_write - shared_context.mp3_buffer_read);
    else
        return shared_context.mp3_buffer_read - shared_context.mp3_buffer_write - 1;
}

/* Must hold audiocore_shared_context.lock */
static inline unsigned audiocore_get_buffer_avail(void)
{
    if (shared_context.mp3_buffer_write >= shared_context.mp3_buffer_read)
        return shared_context.mp3_buffer_write - shared_context.mp3_buffer_read;
    else
        return MP3_BUFFER_SIZE - (shared_context.mp3_buffer_read - shared_context.mp3_buffer_write);
}

/* Must hold audiocore_shared_context.lock */
static inline void audiocore_buffer_put(const char *restrict src, const size_t len)
{
    const unsigned end_bytes = MP3_BUFFER_SIZE - shared_context.mp3_buffer_write;
    memcpy(shared_context.mp3_buffer + MP3_BUFFER_PREAREA + shared_context.mp3_buffer_write, src,
           ((end_bytes >= len) ? len : end_bytes));
    if (end_bytes < len) {
        memcpy(shared_context.mp3_buffer + MP3_BUFFER_PREAREA, src + end_bytes, len - end_bytes);
        shared_context.mp3_buffer_write = len - end_bytes;
    } else {
        shared_context.mp3_buffer_write += len;
    }
    shared_context.mp3_buffer_write %= MP3_BUFFER_SIZE;
}

void __time_critical_func(volume_adjust)(int16_t *buf, size_t samples, uint16_t scalef);

void core1_main(void);

// For data sent from core1 to core0, signals that this is a return value from some function call
// Otherwise it it just a trigger to wake core0 and the data can be discarded.
#define AUDIOCORE_FIFO_DATA_FLAG 0x80000000

// SHUTDOWN - no arguments - return 0
#define AUDIOCORE_CMD_SHUTDOWN 0xdeadc0de

// FLUSH - signals end of file and stop decoding when buffer empty - no arguments - return 0 when decoding is finished
#define AUDIOCORE_CMD_FLUSH 0xdeadc0dd

#define AUDIOCORE_MAX_VOLUME 0x8000u
// SET VOLUME - one argument: uint32_t range 0 to AUDIOCORE_MAX_VOLUME - return 0 if volume changed, 1 on error
#define AUDIOCORE_CMD_SET_VOLUME 0xdead0001
