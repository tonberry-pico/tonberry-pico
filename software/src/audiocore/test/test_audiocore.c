// SPDX-License-Identifier: MIT
// Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

#include "audiocore.h"
#include "i2s.h"
#include "py/mperrno.h"

#include "unity.h"

struct audiocore_shared_context shared_context;

static bool i2s_init_return;
static bool i2s_initialized = false;
static unsigned multicore_fifo_push_last;

static unsigned (*multicore_fifo_pop_blocking_cb)(void);

bool i2s_init(int out_pin, int sideset_base, int samplerate)
{
    TEST_ASSERT_FALSE(i2s_initialized);
    if (i2s_init_return)
        i2s_initialized = true;
    return i2s_init_return;
}

void i2s_deinit(void)
{
    TEST_ASSERT_TRUE(i2s_initialized);
    i2s_initialized = false;
}

void multicore_fifo_push_blocking(unsigned val) { multicore_fifo_push_last = val; }

unsigned multicore_fifo_pop_blocking(void)
{
    if (multicore_fifo_pop_blocking_cb)
        return multicore_fifo_pop_blocking_cb();
    return 0;
}

void test_audiocore_handles_i2sinit_failure(void)
{
    i2s_init_return = false;
    core1_main();
    TEST_ASSERT_EQUAL(multicore_fifo_push_last, MP_EIO);
}

unsigned audiocore_init_deinit_pop_cb(void)
{
    TEST_ASSERT_EQUAL(0, multicore_fifo_push_last);
    TEST_ASSERT_TRUE(i2s_initialized);
    return AUDIOCORE_CMD_SHUTDOWN;
}

void test_audiocore_init_deinit(void)
{
    multicore_fifo_pop_blocking_cb = &audiocore_init_deinit_pop_cb;
    i2s_init_return = true;

    core1_main();
    TEST_ASSERT_EQUAL(0, multicore_fifo_push_last);
    TEST_ASSERT_FALSE(i2s_initialized);
}

void test_audiocore_buffer_space(void)
{
    // empty ring buffer
    shared_context.audio_buffer_read = shared_context.audio_buffer_write = 0;
    TEST_ASSERT_EQUAL(AUDIO_BUFFER_SIZE - 1, audiocore_get_audio_buffer_space());

    shared_context.audio_buffer_read = shared_context.audio_buffer_write = 23;
    TEST_ASSERT_EQUAL(AUDIO_BUFFER_SIZE - 1, audiocore_get_audio_buffer_space());

    shared_context.audio_buffer_read = shared_context.audio_buffer_write = AUDIO_BUFFER_SIZE - 1;
    TEST_ASSERT_EQUAL(AUDIO_BUFFER_SIZE - 1, audiocore_get_audio_buffer_space());

    // full ring buffer
    shared_context.audio_buffer_write = 0;
    shared_context.audio_buffer_read = 1;
    TEST_ASSERT_EQUAL(0, audiocore_get_audio_buffer_space());

    shared_context.audio_buffer_write = AUDIO_BUFFER_SIZE - 1;
    shared_context.audio_buffer_read = 0;
    TEST_ASSERT_EQUAL(0, audiocore_get_audio_buffer_space());

    // write > read
    shared_context.audio_buffer_write = 10;
    shared_context.audio_buffer_read = 0;
    TEST_ASSERT_EQUAL(AUDIO_BUFFER_SIZE - 1 - 10, audiocore_get_audio_buffer_space());

    // write < read
    shared_context.audio_buffer_write = 0;
    shared_context.audio_buffer_read = 10;
    TEST_ASSERT_EQUAL(9, audiocore_get_audio_buffer_space());
}

void test_audiocore_buffer_avail(void)
{
    // empty ring buffer
    shared_context.audio_buffer_read = shared_context.audio_buffer_write = 0;
    TEST_ASSERT_EQUAL(0, audiocore_get_audio_buffer_avail());

    shared_context.audio_buffer_read = shared_context.audio_buffer_write = 23;
    TEST_ASSERT_EQUAL(0, audiocore_get_audio_buffer_avail());

    shared_context.audio_buffer_read = shared_context.audio_buffer_write = AUDIO_BUFFER_SIZE - 1;
    TEST_ASSERT_EQUAL(0, audiocore_get_audio_buffer_avail());

    // full ring buffer
    shared_context.audio_buffer_write = 0;
    shared_context.audio_buffer_read = 1;
    TEST_ASSERT_EQUAL(AUDIO_BUFFER_SIZE - 1, audiocore_get_audio_buffer_avail());

    shared_context.audio_buffer_write = AUDIO_BUFFER_SIZE - 1;
    shared_context.audio_buffer_read = 0;
    TEST_ASSERT_EQUAL(AUDIO_BUFFER_SIZE - 1, audiocore_get_audio_buffer_avail());

    // write > read
    shared_context.audio_buffer_write = 10;
    shared_context.audio_buffer_read = 0;
    TEST_ASSERT_EQUAL(10, audiocore_get_audio_buffer_avail());

    // write < read
    shared_context.audio_buffer_write = 0;
    shared_context.audio_buffer_read = 10;
    TEST_ASSERT_EQUAL(AUDIO_BUFFER_SIZE - 10, audiocore_get_audio_buffer_avail());
}

static unsigned fill_buffer_helper(void)
{
    uint32_t test_data[100];
    uint32_t ctr = 0;

    unsigned avail, filled = 0;
    while ((avail = audiocore_get_audio_buffer_space()) > 0) {
        const unsigned todo = avail > 100 ? 100 : avail;
        for (unsigned i = 0; i < todo; ++i)
            test_data[i] = ctr++;
        audiocore_audio_buffer_put(test_data, todo);
        filled += todo;
    }
    return filled;
}

void test_audiocore_buffer_put(void)
{
    shared_context.audio_buffer_read = shared_context.audio_buffer_write = 0;

    TEST_ASSERT_EQUAL(AUDIO_BUFFER_SIZE - 1, fill_buffer_helper());
    for (unsigned i = 0; i < AUDIO_BUFFER_SIZE - 1; ++i) {
        TEST_ASSERT_EQUAL(i, shared_context.audio_buffer[i]);
    }

    // test wraparound fill
    shared_context.audio_buffer_read = shared_context.audio_buffer_write = AUDIO_BUFFER_SIZE - 10;
    TEST_ASSERT_EQUAL(AUDIO_BUFFER_SIZE - 1, fill_buffer_helper());
    for (unsigned i = 0; i < AUDIO_BUFFER_SIZE - 1; ++i) {
        TEST_ASSERT_EQUAL(i, shared_context.audio_buffer[(i + AUDIO_BUFFER_SIZE - 10) % AUDIO_BUFFER_SIZE]);
    }
}

static unsigned get_buffer_helper(void)
{
    uint32_t test_data[100];
    uint32_t ctr = 0;

    unsigned avail, gotten = 0;
    while ((avail = audiocore_get_audio_buffer_avail()) > 0) {
        const unsigned todo = avail > 100 ? 100 : avail;
        audiocore_audio_buffer_get(test_data, todo);
        for (unsigned i = 0; i < todo; ++i)
            TEST_ASSERT_EQUAL(ctr++, test_data[i]);
        gotten += todo;
    }
    return gotten;
}

void test_audiocore_buffer_get(void)
{
    shared_context.audio_buffer_read = 0;
    shared_context.audio_buffer_write = AUDIO_BUFFER_SIZE - 1;
    for (unsigned i = 0; i < AUDIO_BUFFER_SIZE - 1; ++i)
        shared_context.audio_buffer[i] = i;
    TEST_ASSERT_EQUAL(AUDIO_BUFFER_SIZE - 1, get_buffer_helper());

    // test wraparound read
    shared_context.audio_buffer_read = 10;
    shared_context.audio_buffer_write = 9;
    for (unsigned i = 0; i < AUDIO_BUFFER_SIZE - 1; ++i)
        shared_context.audio_buffer[(i + 10) % AUDIO_BUFFER_SIZE] = i;
    TEST_ASSERT_EQUAL(AUDIO_BUFFER_SIZE - 1, get_buffer_helper());
}
