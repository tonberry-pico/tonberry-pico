// SPDX-License-Identifier: MIT
// Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

#include "audiocore.h"
#include "i2s_max98357.pio.h"

#include <hardware/dma.h>
#include <hardware/sync.h>

#include <string.h>

#define audiocore_pio pio1

#define I2S_DMA_BUF_SIZE 256

struct i2s_context {
    unsigned pio_program_offset;
    int pio_sm;
    int dma_ch;
    dma_channel_config dma_config;
    uint32_t dma_buf[I2S_DMA_BUF_SIZE];
};

static struct i2s_context i2s_context;

static void dma_isr(void)
{
    if (!dma_channel_get_irq1_status(i2s_context.dma_ch))
        return;
    dma_channel_acknowledge_irq1(i2s_context.dma_ch);
    const uint32_t flags = spin_lock_blocking(shared_context.lock);
    if (audiocore_get_audio_buffer_avail() >= I2S_DMA_BUF_SIZE) {
        audiocore_audio_buffer_get(i2s_context.dma_buf, I2S_DMA_BUF_SIZE);
        spin_unlock(shared_context.lock, flags);
    } else {
        ++shared_context.underruns;
        spin_unlock(shared_context.lock, flags);
        memset(i2s_context.dma_buf, 0, sizeof(uint32_t) * I2S_DMA_BUF_SIZE);
    }
    dma_channel_transfer_from_buffer_now(i2s_context.dma_ch, i2s_context.dma_buf, I2S_DMA_BUF_SIZE);
}

static void setup_dma_config(void)
{
    i2s_context.dma_config = dma_channel_get_default_config(i2s_context.dma_ch);
    channel_config_set_dreq(&i2s_context.dma_config, pio_get_dreq(pio1, i2s_context.pio_sm, true));
}

bool i2s_init(int out_pin, int sideset_base, int samplerate)
{
    memset(i2s_context.dma_buf, 0, sizeof(i2s_context.dma_buf[0]) * I2S_DMA_BUF_SIZE);
    if (!pio_can_add_program(audiocore_pio, &i2s_max98357_program))
        return false;
    i2s_context.pio_sm = pio_claim_unused_sm(audiocore_pio, false);
    if (i2s_context.pio_sm == -1)
        return false;
    i2s_context.pio_program_offset = pio_add_program(audiocore_pio, &i2s_max98357_program);
    i2s_max98357_program_init(audiocore_pio, i2s_context.pio_sm, i2s_context.pio_program_offset, out_pin, sideset_base,
                              samplerate);

    i2s_context.dma_ch = dma_claim_unused_channel(false);
    if (i2s_context.dma_ch == -1)
        goto out_dma_claim;
    setup_dma_config();
    irq_set_exclusive_handler(DMA_IRQ_1, &dma_isr);
    dma_channel_set_irq1_enabled(i2s_context.dma_ch, true);
    irq_set_enabled(DMA_IRQ_1, true);
    dma_channel_configure(i2s_context.dma_ch, &i2s_context.dma_config, &audiocore_pio->txf[i2s_context.pio_sm],
                          i2s_context.dma_buf, I2S_DMA_BUF_SIZE, true);
    pio_sm_set_enabled(audiocore_pio, i2s_context.pio_sm, true);

    return true;

out_dma_claim:
    pio_remove_program(audiocore_pio, &i2s_max98357_program, i2s_context.pio_program_offset);
    pio_sm_unclaim(audiocore_pio, i2s_context.pio_sm);
    return false;
}

void i2s_deinit(void)
{
    pio_sm_set_enabled(audiocore_pio, i2s_context.pio_sm, false);
    dma_channel_set_irq1_enabled(i2s_context.dma_ch, false);
    dma_channel_unclaim(i2s_context.dma_ch);
    pio_remove_program(audiocore_pio, &i2s_max98357_program, i2s_context.pio_program_offset);
    pio_sm_unclaim(audiocore_pio, i2s_context.pio_sm);
}
