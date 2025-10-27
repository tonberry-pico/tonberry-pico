// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2025 Matthias Blankertz <matthias@blankertz.org>

#include "i2s.h"
#include "i2s_max98357.pio.h"

#include "audiocore.h"

#include <hardware/dma.h>
#include <hardware/sync.h>

#include <stdio.h>
#include <string.h>

#define audiocore_pio pio1

// Must be at least 2
#define AUDIO_BUFS 2

struct i2s_context {
    unsigned pio_program_offset;
    int pio_sm;
    int dma_ch;
    dma_channel_config dma_config;
    uint32_t dma_buf[AUDIO_BUFS][I2S_DMA_BUF_SIZE];
    int cur_playing;
    int out_pin, sideset_base;
    bool has_data[AUDIO_BUFS];
    bool playback_active;
};

static struct i2s_context i2s_context;

static void __time_critical_func(dma_isr)(void)
{
    if (get_core_num() != 1 || !dma_channel_get_irq1_status(i2s_context.dma_ch))
        return;
    dma_channel_acknowledge_irq1(i2s_context.dma_ch);
    const int next_buf = (i2s_context.cur_playing + 1) % AUDIO_BUFS;
    if (i2s_context.playback_active && i2s_context.has_data[next_buf]) {
        i2s_context.cur_playing = next_buf;
        i2s_context.has_data[next_buf] = false;
    } else {
        memset(i2s_context.dma_buf[i2s_context.cur_playing], 0, sizeof(uint32_t) * I2S_DMA_BUF_SIZE);
        if (i2s_context.playback_active) {
            ++shared_context.underruns;
        }
    }
    dma_channel_transfer_from_buffer_now(i2s_context.dma_ch, i2s_context.dma_buf[i2s_context.cur_playing],
                                         I2S_DMA_BUF_SIZE);
}

static void setup_dma_config(void)
{
    i2s_context.dma_config = dma_channel_get_default_config(i2s_context.dma_ch);
    channel_config_set_dreq(&i2s_context.dma_config, pio_get_dreq(pio1, i2s_context.pio_sm, true));
}

uint32_t *__time_critical_func(i2s_next_buf)(void)
{
    uint32_t *ret = NULL;
    const long flags = save_and_disable_interrupts();
    for (int i = 1; i < AUDIO_BUFS; ++i) {
        const int next_buf = (i2s_context.cur_playing + i) % AUDIO_BUFS;
        if (!i2s_context.has_data[next_buf]) {
            ret = i2s_context.dma_buf[next_buf];
            break;
        }
    }
    restore_interrupts(flags);
    return ret;
}

void __time_critical_func(i2s_commit_buf)(uint32_t *buf)
{
    const long flags = save_and_disable_interrupts();
    for (int i = 1; i < AUDIO_BUFS; ++i) {
        const int next_buf = (i2s_context.cur_playing + i) % AUDIO_BUFS;
        if (i2s_context.dma_buf[next_buf] == buf) {
            i2s_context.has_data[next_buf] = true;
            if (i == AUDIO_BUFS - 1) {
                i2s_context.playback_active = true;
            }
            break;
        }
    }
    restore_interrupts(flags);
}

void i2s_stop(void)
{
    if (!i2s_context.playback_active)
        return;
    while (true) {
        const long flags = save_and_disable_interrupts();
        const int next_buf = (i2s_context.cur_playing + 1) % AUDIO_BUFS;
        const bool have_data = i2s_context.has_data[next_buf];
        if (!have_data) {
            i2s_context.playback_active = false;
            shared_context.underruns = 0;
            restore_interrupts(flags);
            break;
        }
        __wfi();
        restore_interrupts(flags);
        __nop(); // Ensure at least two instructions between enable interrupts and subsequent disable
        __nop();
    }
    // Workaround rp2040 E13
    dma_channel_set_irq1_enabled(i2s_context.dma_ch, false);
    dma_channel_abort(i2s_context.dma_ch);
    dma_channel_acknowledge_irq1(i2s_context.dma_ch);
    dma_channel_set_irq1_enabled(i2s_context.dma_ch, true);
    pio_sm_set_enabled(audiocore_pio, i2s_context.pio_sm, false);
    pio_sm_clear_fifos(audiocore_pio, i2s_context.pio_sm);
}

bool i2s_init(int out_pin, int sideset_base, bool dclk_first)
{
    memset(i2s_context.dma_buf, 0, sizeof(i2s_context.dma_buf[0][0]) * AUDIO_BUFS * I2S_DMA_BUF_SIZE);
    const pio_program_t *program = dclk_first ? &i2s_max98357_program : &i2s_max98357_lrclk_program;
    if (!pio_can_add_program(audiocore_pio, program))
        return false;
    i2s_context.pio_sm = pio_claim_unused_sm(audiocore_pio, false);
    i2s_context.out_pin = out_pin;
    i2s_context.sideset_base = sideset_base;
    if (i2s_context.pio_sm == -1)
        return false;
    i2s_context.pio_program_offset = pio_add_program(audiocore_pio, program);

    i2s_context.dma_ch = dma_claim_unused_channel(false);
    if (i2s_context.dma_ch == -1)
        goto out_dma_claim;
    i2s_context.playback_active = false;
    setup_dma_config();
    irq_add_shared_handler(DMA_IRQ_1, &dma_isr, PICO_SHARED_IRQ_HANDLER_DEFAULT_ORDER_PRIORITY);
    dma_channel_set_irq1_enabled(i2s_context.dma_ch, true);
    irq_set_enabled(DMA_IRQ_1, true);
    return true;

out_dma_claim:
    pio_remove_program(audiocore_pio, (const pio_program_t *)&i2s_max98357_program, i2s_context.pio_program_offset);
    pio_sm_unclaim(audiocore_pio, i2s_context.pio_sm);
    return false;
}

void i2s_play(int samplerate)
{
    i2s_context.playback_active = false;
    i2s_context.cur_playing = 0;
    memset(i2s_context.dma_buf, 0, sizeof(i2s_context.dma_buf[0][0]) * AUDIO_BUFS * I2S_DMA_BUF_SIZE);
    i2s_max98357_program_init(audiocore_pio, i2s_context.pio_sm, i2s_context.pio_program_offset, i2s_context.out_pin,
                              i2s_context.sideset_base, samplerate);
    dma_channel_configure(i2s_context.dma_ch, &i2s_context.dma_config, &audiocore_pio->txf[i2s_context.pio_sm],
                          i2s_context.dma_buf, I2S_DMA_BUF_SIZE, true);
    pio_sm_set_enabled(audiocore_pio, i2s_context.pio_sm, true);
}

void i2s_deinit(void)
{
    pio_sm_set_enabled(audiocore_pio, i2s_context.pio_sm, false);
    dma_channel_set_irq1_enabled(i2s_context.dma_ch, false);
    dma_channel_abort(i2s_context.dma_ch);
    irq_remove_handler(DMA_IRQ_1, &dma_isr);
    dma_channel_unclaim(i2s_context.dma_ch);
    pio_remove_program(audiocore_pio, &i2s_max98357_program, i2s_context.pio_program_offset);
    pio_sm_unclaim(audiocore_pio, i2s_context.pio_sm);
}
