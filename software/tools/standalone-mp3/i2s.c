#include "i2s.h"
#include "i2s_max98357.pio.h"

#include <hardware/dma.h>
#include <hardware/sync.h>

#include <string.h>
#include <stdio.h>

#define audiocore_pio pio1

#define AUDIO_BUFS 3

struct i2s_context {
    unsigned pio_program_offset;
    int pio_sm;
    int dma_ch;
    dma_channel_config dma_config;
    uint32_t dma_buf[AUDIO_BUFS][I2S_DMA_BUF_SIZE];
    int cur_playing;
    bool has_data[AUDIO_BUFS];
    bool playback_active;
};

static struct i2s_context i2s_context;

#define OUT_PIN 8
#define SIDESET_BASE 6

static void dma_isr(void)
{
    if (!dma_channel_get_irq1_status(i2s_context.dma_ch))
        return;
    dma_channel_acknowledge_irq1(i2s_context.dma_ch);
    const int next_buf = (i2s_context.cur_playing + 1) % AUDIO_BUFS;
    if (i2s_context.playback_active && i2s_context.has_data[next_buf]) {
        i2s_context.cur_playing = next_buf;
        i2s_context.has_data[next_buf] = false;
    } else {
        memset(i2s_context.dma_buf[i2s_context.cur_playing], 0, sizeof(uint32_t) * I2S_DMA_BUF_SIZE);
        if (i2s_context.playback_active)
            printf("x");
    }
    dma_channel_transfer_from_buffer_now(i2s_context.dma_ch, i2s_context.dma_buf[i2s_context.cur_playing], I2S_DMA_BUF_SIZE);
}

static void setup_dma_config(void)
{
    i2s_context.dma_config = dma_channel_get_default_config(i2s_context.dma_ch);
    channel_config_set_dreq(&i2s_context.dma_config, pio_get_dreq(pio1, i2s_context.pio_sm, true));
}

uint32_t *i2s_next_buf(void)
{
    const long flags = save_and_disable_interrupts();
    const int next_buf = (i2s_context.cur_playing + 1) % AUDIO_BUFS;
    uint32_t *ret = NULL;
    if (!i2s_context.has_data[next_buf]) {
        ret = i2s_context.dma_buf[next_buf];
    } else {
        const int next_buf_2 = (next_buf + 1) % AUDIO_BUFS;
        if (!i2s_context.has_data[next_buf_2]) {
            ret = i2s_context.dma_buf[next_buf_2];
        }
    }
    restore_interrupts(flags);
    return ret;
}

void i2s_commit_buf(uint32_t *buf)
{
    const long flags = save_and_disable_interrupts();
    const int next_buf = (i2s_context.cur_playing + 1) % AUDIO_BUFS;
    const int next_buf_2 = (next_buf + 1) % AUDIO_BUFS;
    if (i2s_context.dma_buf[next_buf] == buf) {
        i2s_context.has_data[next_buf] = true;
    } else if (i2s_context.dma_buf[next_buf_2] == buf) {
        i2s_context.has_data[next_buf_2] = true;
        i2s_context.playback_active = true;
    } else {
        assert(false);
    }
    restore_interrupts(flags);
}

bool i2s_init(int samplerate)
{
    memset(i2s_context.dma_buf, 0, sizeof(i2s_context.dma_buf[0][0]) * 2* I2S_DMA_BUF_SIZE);
    if (!pio_can_add_program(audiocore_pio, (const pio_program_t *)&i2s_max98357_program))
        return false;
    i2s_context.pio_sm = pio_claim_unused_sm(audiocore_pio, false);
    if (i2s_context.pio_sm == -1)
        return false;
    i2s_context.pio_program_offset = pio_add_program(audiocore_pio, (const pio_program_t *)&i2s_max98357_program);
    i2s_max98357_program_init(audiocore_pio, i2s_context.pio_sm, i2s_context.pio_program_offset, OUT_PIN, SIDESET_BASE,
                              samplerate);

    i2s_context.dma_ch = dma_claim_unused_channel(false);
    if (i2s_context.dma_ch == -1)
        goto out_dma_claim;
    i2s_context.playback_active = false;
    setup_dma_config();
    irq_add_shared_handler(DMA_IRQ_1, &dma_isr, PICO_SHARED_IRQ_HANDLER_DEFAULT_ORDER_PRIORITY);
    dma_channel_set_irq1_enabled(i2s_context.dma_ch, true);
    irq_set_enabled(DMA_IRQ_1, true);
    dma_channel_configure(i2s_context.dma_ch, &i2s_context.dma_config, &audiocore_pio->txf[i2s_context.pio_sm],
                          i2s_context.dma_buf, I2S_DMA_BUF_SIZE, true);
    pio_sm_set_enabled(audiocore_pio, i2s_context.pio_sm, true);

    return true;

out_dma_claim:
    pio_remove_program(audiocore_pio, (const pio_program_t *)&i2s_max98357_program, i2s_context.pio_program_offset);
    pio_sm_unclaim(audiocore_pio, i2s_context.pio_sm);
    return false;
}
