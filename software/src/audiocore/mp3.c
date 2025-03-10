// SPDX-License-Identifier: MIT
// Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

#include "mp3.h"
#include "audiocore.h"
#include "mp3dec.h"

#include <stdio.h>
#include <string.h>

static HMP3Decoder mp3dec;
static bool synced = false;
static size_t prearea_fill = 0;
#ifdef MP3_DEBUG
static first = true;
#endif

bool mp3_init(void)
{
    mp3dec = MP3InitDecoder();
    return (mp3dec != 0);
}

void mp3_deinit(void)
{
    if (mp3dec) {
        MP3FreeDecoder(mp3dec);
        mp3dec = NULL;
    }
}

static size_t __time_critical_func(mp3_get_continuous_data)(unsigned char **readptr)
{
    size_t bytes_left;
    const uint32_t flags = spin_lock_blocking(shared_context.lock);
    /* Check if remaining bytes at end of buffer should be moved to prearea */
    const unsigned end_bytes = MP3_BUFFER_SIZE - shared_context.mp3_buffer_read;
    if (shared_context.mp3_buffer_write < shared_context.mp3_buffer_read && end_bytes <= MP3_BUFFER_PREAREA) {
        assert(prearea_fill == 0);
        memcpy(shared_context.mp3_buffer + MP3_BUFFER_PREAREA - end_bytes,
               shared_context.mp3_buffer + MP3_BUFFER_PREAREA + shared_context.mp3_buffer_read, end_bytes);
        prearea_fill = end_bytes;
        shared_context.mp3_buffer_read = 0;
    }
    /* Get start and length of valid continuous data */
    if (shared_context.mp3_buffer_read == 0) {
        *readptr = (unsigned char *)(shared_context.mp3_buffer + MP3_BUFFER_PREAREA - prearea_fill);
        bytes_left = prearea_fill + shared_context.mp3_buffer_write;
    } else if (shared_context.mp3_buffer_write < shared_context.mp3_buffer_read) {
        *readptr = (unsigned char *)(shared_context.mp3_buffer + MP3_BUFFER_PREAREA + shared_context.mp3_buffer_read);
        bytes_left = end_bytes;
    } else {
        *readptr = (unsigned char *)(shared_context.mp3_buffer + MP3_BUFFER_PREAREA + shared_context.mp3_buffer_read);
        bytes_left = shared_context.mp3_buffer_write - shared_context.mp3_buffer_read;
    }
    spin_unlock(shared_context.lock, flags);
    return bytes_left;
}

static void __time_critical_func(mp3_consume_data)(size_t bytes_used)
{
    if (prearea_fill >= bytes_used) {
        prearea_fill -= bytes_used;
        return;
    } else {
        bytes_used -= prearea_fill;
        prearea_fill = 0;
    }
    const uint32_t flags = spin_lock_blocking(shared_context.lock);
    shared_context.mp3_buffer_read += bytes_used;
    shared_context.mp3_buffer_read %= MP3_BUFFER_SIZE;
    spin_unlock(shared_context.lock, flags);
}

bool __time_critical_func(mp3_decode)(uint32_t pcm_buf[static 1152], unsigned *samplerate)
{
    unsigned char *readptr;
    size_t bytes_avail = mp3_get_continuous_data(&readptr);
    if (!bytes_avail)
        return false;
    if (!synced) {
        const int ofs = MP3FindSyncWord((unsigned char *)readptr, bytes_avail);
        if (ofs == -1) {
#ifdef MP3_DEBUG
            printf("MP3 sync word not found\n");
#endif
            mp3_consume_data(bytes_avail);
            return false;
        }

        readptr += ofs;
        bytes_avail -= ofs;
        mp3_consume_data(ofs);
#ifdef MP3_DEBUG
        printf("MP3 sync word found after %zu bytes\n", ofs);
#endif
        synced = true;
    }
    if (!bytes_avail)
        return false;

    // Decode one frame
    int int_bytes_avail = bytes_avail;
    const int status = MP3Decode(mp3dec, &readptr, &int_bytes_avail, (short *)pcm_buf, 0);
    if (status) {
        if (status == ERR_MP3_INDATA_UNDERFLOW) {
            return false;
        } else /*if (status== ERR_MP3_MAINDATA_UNDERFLOW)*/ {
            mp3_consume_data(1);
            synced = false;
            return false;
        }
    }
    mp3_consume_data(bytes_avail - int_bytes_avail);
    MP3FrameInfo info;
    MP3GetLastFrameInfo(mp3dec, &info);
#ifdef MP3_DEBUG
    if (first) {
        printf("bitrate %d, nChans %d, samprate %d, bitsPerSample %d, outputSamps %d, layer %d, version %d\n",
               info.bitrate, info.nChans, info.samprate, info.bitsPerSample, info.outputSamps, info.layer,
               info.version);
        first = false;
    }
#endif
    *samplerate = info.samprate;

    if (info.outputSamps != 2304) {
#ifdef MP3_DEBUG
        printf("Unexpected number of output samples: %d\n", info.outputSamps);
#endif
        return false;
    }
    return true;
}

void mp3_reset(void)
{
    synced = false;
    prearea_fill = 0;
#ifdef MP3_DEBUG
    first = true;
#endif
    const uint32_t flags = spin_lock_blocking(shared_context.lock);
    shared_context.mp3_buffer_read = shared_context.mp3_buffer_write = 0;
    spin_unlock(shared_context.lock, flags);
}
