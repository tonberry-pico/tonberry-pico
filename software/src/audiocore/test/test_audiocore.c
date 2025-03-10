// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2025 Matthias Blankertz <matthias@blankertz.org>

#include "audiocore.h"
#include "i2s.h"
#include "py/mperrno.h"

#include "unity.h"

struct audiocore_shared_context shared_context;

static bool i2s_init_return;
static bool i2s_initialized = false;
static unsigned multicore_fifo_push_last;

static unsigned (*multicore_fifo_pop_blocking_cb)(void);

bool i2s_init(int out_pin, int sideset_base)
{
    TEST_ASSERT_FALSE(i2s_initialized);
    if (i2s_init_return)
        i2s_initialized = true;
    return i2s_init_return;
}

uint32_t *i2s_next_buf(void) { return NULL; }

void i2s_commit_buf(uint32_t *buf) {}

void i2s_play(int samplerate) {}

void i2s_stop(void) {}

void i2s_deinit(void)
{
    TEST_ASSERT_TRUE(i2s_initialized);
    i2s_initialized = false;
}

bool mp3_init(void) { return true; }

void mp3_deinit(void) {}

bool mp3_decode(uint32_t pcm_buf[static 1152], unsigned *samplerate) { return false; }

void mp3_reset(void) {}

void multicore_fifo_push_blocking(unsigned val) { multicore_fifo_push_last = val; }

unsigned multicore_fifo_pop_blocking(void)
{
    if (multicore_fifo_pop_blocking_cb)
        return multicore_fifo_pop_blocking_cb();
    return 0;
}

bool multicore_fifo_rvalid(void) { return multicore_fifo_pop_blocking_cb; }

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
    shared_context.mp3_buffer_read = shared_context.mp3_buffer_write = 0;
    TEST_ASSERT_EQUAL(MP3_BUFFER_SIZE - 1, audiocore_get_buffer_space());

    shared_context.mp3_buffer_read = shared_context.mp3_buffer_write = 23;
    TEST_ASSERT_EQUAL(MP3_BUFFER_SIZE - 1, audiocore_get_buffer_space());

    shared_context.mp3_buffer_read = shared_context.mp3_buffer_write = MP3_BUFFER_SIZE - 1;
    TEST_ASSERT_EQUAL(MP3_BUFFER_SIZE - 1, audiocore_get_buffer_space());

    // full ring buffer
    shared_context.mp3_buffer_write = 0;
    shared_context.mp3_buffer_read = 1;
    TEST_ASSERT_EQUAL(0, audiocore_get_buffer_space());

    shared_context.mp3_buffer_write = MP3_BUFFER_SIZE - 1;
    shared_context.mp3_buffer_read = 0;
    TEST_ASSERT_EQUAL(0, audiocore_get_buffer_space());

    // write > read
    shared_context.mp3_buffer_write = 10;
    shared_context.mp3_buffer_read = 0;
    TEST_ASSERT_EQUAL(MP3_BUFFER_SIZE - 1 - 10, audiocore_get_buffer_space());

    // write < read
    shared_context.mp3_buffer_write = 0;
    shared_context.mp3_buffer_read = 10;
    TEST_ASSERT_EQUAL(9, audiocore_get_buffer_space());
}

void test_audiocore_buffer_avail(void)
{
    // empty ring buffer
    shared_context.mp3_buffer_read = shared_context.mp3_buffer_write = 0;
    TEST_ASSERT_EQUAL(0, audiocore_get_buffer_avail());

    shared_context.mp3_buffer_read = shared_context.mp3_buffer_write = 23;
    TEST_ASSERT_EQUAL(0, audiocore_get_buffer_avail());

    shared_context.mp3_buffer_read = shared_context.mp3_buffer_write = MP3_BUFFER_SIZE - 1;
    TEST_ASSERT_EQUAL(0, audiocore_get_buffer_avail());

    // full ring buffer
    shared_context.mp3_buffer_write = 0;
    shared_context.mp3_buffer_read = 1;
    TEST_ASSERT_EQUAL(MP3_BUFFER_SIZE - 1, audiocore_get_buffer_avail());

    shared_context.mp3_buffer_write = MP3_BUFFER_SIZE - 1;
    shared_context.mp3_buffer_read = 0;
    TEST_ASSERT_EQUAL(MP3_BUFFER_SIZE - 1, audiocore_get_buffer_avail());

    // write > read
    shared_context.mp3_buffer_write = 10;
    shared_context.mp3_buffer_read = 0;
    TEST_ASSERT_EQUAL(10, audiocore_get_buffer_avail());

    // write < read
    shared_context.mp3_buffer_write = 0;
    shared_context.mp3_buffer_read = 10;
    TEST_ASSERT_EQUAL(MP3_BUFFER_SIZE - 10, audiocore_get_buffer_avail());
}

static unsigned fill_buffer_helper(void)
{
    char test_data[100];
    uint32_t ctr = 0;

    unsigned avail, filled = 0;
    while ((avail = audiocore_get_buffer_space()) > 0) {
        const unsigned todo = avail > 100 ? 100 : avail;
        for (unsigned i = 0; i < todo; ++i)
            test_data[i] = ctr++;
        audiocore_buffer_put(test_data, todo);
        filled += todo;
    }
    return filled;
}

void test_audiocore_buffer_put(void)
{
    shared_context.mp3_buffer_read = shared_context.mp3_buffer_write = 0;

    TEST_ASSERT_EQUAL(MP3_BUFFER_SIZE - 1, fill_buffer_helper());
    for (unsigned i = 0; i < MP3_BUFFER_SIZE - 1; ++i) {
        TEST_ASSERT_EQUAL((char)(i & 0xFF), shared_context.mp3_buffer[MP3_BUFFER_PREAREA + i]);
    }

    // test wraparound fill
    shared_context.mp3_buffer_read = shared_context.mp3_buffer_write = MP3_BUFFER_SIZE - 10;
    TEST_ASSERT_EQUAL(MP3_BUFFER_SIZE - 1, fill_buffer_helper());
    for (unsigned i = 0; i < MP3_BUFFER_SIZE - 1; ++i) {
        TEST_ASSERT_EQUAL(
            (char)(i & 0xFF),
            shared_context.mp3_buffer[MP3_BUFFER_PREAREA + ((i + MP3_BUFFER_SIZE - 10) % MP3_BUFFER_SIZE)]);
    }
}

void test_audiocore_volume_adjust(void)
{
    const int16_t samples[] = {0, 1, -1, INT16_MIN, INT16_MAX, 100, -100, 99, -99};
#define SAMPLE_COUNT (sizeof(samples) / sizeof(samples[0]))
    const struct {
        uint16_t scalefactor;
        int16_t expected[SAMPLE_COUNT];
    } expected[] = {
        {.scalefactor = AUDIOCORE_MAX_VOLUME, .expected = {0, 1, -1, INT16_MIN, INT16_MAX, 100, -100, 99, -99}},
        {.scalefactor = 0, .expected = {0}},
        {.scalefactor = AUDIOCORE_MAX_VOLUME / 2, .expected = {0, 0, -1, -16384, 16383, 50, -50, 49, -50}}};

    for (int test = 0; test < sizeof(expected) / sizeof(expected[0]); ++test) {
        int16_t buf[sizeof(samples) / sizeof(samples[0])];
        memcpy(buf, samples, sizeof(samples));
        volume_adjust(buf, SAMPLE_COUNT, expected[test].scalefactor);
        TEST_ASSERT_EQUAL_HEX16_ARRAY(expected[test].expected, buf, SAMPLE_COUNT);
    }
}
