#include "hardware/pio.h"

#include "sd_spi.h"
#include "sd_util.h"

#include "sd_spi_pio.pio.h"

#include "hardware/dma.h"
#include <hardware/gpio.h>
#include <hardware/spi.h>
#include <hardware/sync.h>
#include <pico/time.h>
#include <string.h>

typedef enum { DMA_READ_TOKEN, DMA_READ, DMA_IDLE } sd_dma_state;

struct sd_dma_context {
    uint8_t *read_buf;
    size_t len;
    uint8_t crc_buf[2];
    uint8_t read_token_buf;
    uint8_t wrdata;
    _Atomic sd_dma_state state;
};

struct sd_spi_context {
    struct sd_dma_context sd_dma_context;
    int spi_sm;
    unsigned spi_offset;
    int spi_dma_rd, spi_dma_wr, spi_dma_rd_crc;
    dma_channel_config spi_dma_rd_cfg, spi_dma_wr_cfg, spi_dma_rd_crc_cfg;
    int mosi, miso, sck, ss;
    bool initialized;
};

/* We only realistically need one context, so reduce overhead by statically allocating it here */
static struct sd_spi_context sd_spi_context = {};

static void __time_critical_func(sd_spi_write_blocking)(const uint8_t *data, size_t len)
{
    if (len == 0)
        return;

    pio_sm_put(SD_PIO, sd_spi_context.spi_sm, data[0] << 24);
    for (size_t i = 1; i < len; ++i) {
        pio_sm_put(SD_PIO, sd_spi_context.spi_sm, data[i] << 24);
        pio_sm_get_blocking(SD_PIO, sd_spi_context.spi_sm);
    }
    pio_sm_get_blocking(SD_PIO, sd_spi_context.spi_sm);

    assert(pio_sm_is_tx_fifo_empty(SD_PIO, sd_spi_context.spi_sm));
    assert(pio_sm_is_rx_fifo_empty(SD_PIO, sd_spi_context.spi_sm));
}

static void __time_critical_func(sd_spi_read_blocking)(uint8_t wrdata, uint8_t *data, size_t len)
{
    if (len == 0)
        return;

    pio_sm_put(SD_PIO, sd_spi_context.spi_sm, wrdata << 24);
    for (size_t i = 0; i < len - 1; ++i) {
        pio_sm_put(SD_PIO, sd_spi_context.spi_sm, wrdata << 24);
        data[i] = pio_sm_get_blocking(SD_PIO, sd_spi_context.spi_sm);
    }
    data[len - 1] = pio_sm_get_blocking(SD_PIO, sd_spi_context.spi_sm);

    assert(pio_sm_is_tx_fifo_empty(SD_PIO, sd_spi_context.spi_sm));
    assert(pio_sm_is_rx_fifo_empty(SD_PIO, sd_spi_context.spi_sm));
}

static void __time_critical_func(sd_spi_dma_isr)(void)
{
    if (dma_channel_get_irq0_status(sd_spi_context.spi_dma_rd)) {
        dma_channel_acknowledge_irq0(sd_spi_context.spi_dma_rd);
        if (sd_spi_context.sd_dma_context.state == DMA_READ_TOKEN) {
            if (sd_spi_context.sd_dma_context.read_token_buf != 0xff) {
                if (sd_spi_context.sd_dma_context.read_token_buf == 0xfe) {
                    channel_config_set_chain_to(&sd_spi_context.spi_dma_rd_cfg, sd_spi_context.spi_dma_rd_crc);
                    channel_config_set_irq_quiet(&sd_spi_context.spi_dma_rd_cfg, true);
                    dma_channel_configure(sd_spi_context.spi_dma_rd, &sd_spi_context.spi_dma_rd_cfg,
                                          sd_spi_context.sd_dma_context.read_buf, &SD_PIO->rxf[sd_spi_context.spi_sm],
                                          sd_spi_context.sd_dma_context.len, false);
                    dma_channel_configure(sd_spi_context.spi_dma_wr, &sd_spi_context.spi_dma_wr_cfg,
                                          &SD_PIO->txf[sd_spi_context.spi_sm], &sd_spi_context.sd_dma_context.wrdata,
                                          sd_spi_context.sd_dma_context.len + 2, false);
                    dma_channel_configure(sd_spi_context.spi_dma_rd_crc, &sd_spi_context.spi_dma_rd_crc_cfg,
                                          sd_spi_context.sd_dma_context.crc_buf, &SD_PIO->rxf[sd_spi_context.spi_sm], 2,
                                          false);
                    dma_start_channel_mask((1 << sd_spi_context.spi_dma_rd) | (1 << sd_spi_context.spi_dma_wr));
                    sd_spi_context.sd_dma_context.state = DMA_READ;
                } else {
                    // Bad read token, abort transfer
                    sd_spi_context.sd_dma_context.state = DMA_IDLE;
                }
            } else {
                // try again
                dma_channel_configure(sd_spi_context.spi_dma_rd, &sd_spi_context.spi_dma_rd_cfg,
                                      &sd_spi_context.sd_dma_context.read_token_buf,
                                      &SD_PIO->rxf[sd_spi_context.spi_sm], 1, false);
                dma_channel_configure(sd_spi_context.spi_dma_wr, &sd_spi_context.spi_dma_wr_cfg,
                                      &SD_PIO->txf[sd_spi_context.spi_sm], &sd_spi_context.sd_dma_context.wrdata, 1,
                                      false);
                dma_start_channel_mask((1 << sd_spi_context.spi_dma_rd) | (1 << sd_spi_context.spi_dma_wr));
            }
        }
    }
    if (dma_channel_get_irq0_status(sd_spi_context.spi_dma_rd_crc)) {
        dma_channel_acknowledge_irq0(sd_spi_context.spi_dma_rd_crc);
        assert(sd_spi_context.sd_dma_context.state == DMA_READ);
        sd_spi_context.sd_dma_context.state = DMA_IDLE;
    }
}

void sd_spi_wait_complete(void)
{
    while (true) {
        const long flags = save_and_disable_interrupts();
        const sd_dma_state state = sd_spi_context.sd_dma_context.state;
        if (state == DMA_IDLE) {
            restore_interrupts(flags);
            return;
        }
        __wfi();
        restore_interrupts(flags);
        __nop(); // Ensure at least two instructions between enable interrupts and subsequent disable
        __nop();
    }
}

bool sd_cmd_read_is_complete(void) { return sd_spi_context.sd_dma_context.state == DMA_IDLE; }

static bool sd_spi_read_dma(uint8_t wrdata, uint8_t *data, size_t len)
{
    if (sd_spi_context.sd_dma_context.state != DMA_IDLE)
        return false;
    channel_config_set_chain_to(&sd_spi_context.spi_dma_rd_cfg, sd_spi_context.spi_dma_rd);
    channel_config_set_irq_quiet(&sd_spi_context.spi_dma_rd_cfg, false);
    dma_channel_configure(sd_spi_context.spi_dma_rd, &sd_spi_context.spi_dma_rd_cfg,
                          &sd_spi_context.sd_dma_context.read_token_buf, &SD_PIO->rxf[sd_spi_context.spi_sm], 1, false);
    dma_channel_configure(sd_spi_context.spi_dma_wr, &sd_spi_context.spi_dma_wr_cfg,
                          &SD_PIO->txf[sd_spi_context.spi_sm], &sd_spi_context.sd_dma_context.wrdata, 1, false);
    sd_spi_context.sd_dma_context.state = DMA_READ_TOKEN;
    sd_spi_context.sd_dma_context.len = len;
    sd_spi_context.sd_dma_context.read_buf = data;
    sd_spi_context.sd_dma_context.wrdata = wrdata;
    dma_start_channel_mask((1 << sd_spi_context.spi_dma_rd) | (1 << sd_spi_context.spi_dma_wr));
    return true;
}

static void sd_spi_cmd_send(const uint8_t cmd, const uint32_t arg)
{
    uint8_t buf[6] = {0x40 | cmd, arg >> 24, arg >> 16, arg >> 8, arg, 0};
    buf[5] = sd_crc7(5, buf) << 1 | 1;
    gpio_put(sd_spi_context.ss, false);
    // Write command, argument and CRC
    sd_spi_write_blocking(buf, 6);
}

bool sd_cmd(const uint8_t cmd, const uint32_t arg, unsigned resplen, uint8_t resp[static resplen])
{
    sd_spi_cmd_send(cmd, arg);
    resp[0] = 0;
    // Read up to 8 garbage bytes (0xff), followed by R1 (MSB is zero)
    bool got_r1 = false;
    for (int timeout = 0; timeout < 8; ++timeout) {
        sd_spi_read_blocking(0xff, resp, 1);
        if (!(resp[0] & 0x80)) {
            got_r1 = true;
            break;
        }
    }
    if (got_r1 && (resp[0] & 0x7e) == 0) {
        // read rest of response if R1 does not indicate an error
        sd_spi_read_blocking(0xff, resp + 1, resplen - 1);
    }
    gpio_put(sd_spi_context.ss, true);
    const uint8_t buf = 0xff;
    // Ensure 8 SPI clock cycles after CS deasserted
    sd_spi_write_blocking(&buf, 1);

    return got_r1 && (resp[0] & 0x7e) == 0;
}

bool sd_cmd_read(uint8_t cmd, uint32_t arg, unsigned datalen, uint8_t data[static datalen])
{
    if (!sd_cmd_read_start(cmd, arg, datalen, data))
        return false;

    return sd_cmd_read_complete();
}

bool sd_cmd_read_start(uint8_t cmd, uint32_t arg, unsigned datalen, uint8_t data[static datalen])
{
    uint8_t buf[2];
    sd_spi_cmd_send(cmd, arg);
    // Read up to 8 garbage bytes (0xff), followed by R1 (MSB is zero)
    bool got_r1 = false;
    for (int timeout = 0; timeout < 8; ++timeout) {
        sd_spi_read_blocking(0xff, buf, 1);
        if (!(buf[0] & 0x80)) {
            got_r1 = true;
            break;
        }
    }
    if (!got_r1 || buf[0] != 0x00)
        goto abort;
    if (!sd_spi_read_dma(0xff, data, datalen))
        goto abort;
    return true;

abort:
    gpio_put(sd_spi_context.ss, true);
    sd_spi_read_blocking(0xff, buf, 1);
    return false;
}

bool sd_cmd_read_complete(void)
{
    uint8_t buf;
    sd_spi_wait_complete();
    gpio_put(sd_spi_context.ss, true);
    sd_spi_read_blocking(0xff, &buf, 1);
    if (sd_spi_context.sd_dma_context.read_token_buf != 0xfe) {
#ifdef SD_DEBUG
        printf("read failed: invalid read token %02hhx\n", sd_spi_context.sd_dma_context.read_token_buf);
#endif
        return false;
    }
#ifdef SD_READ_CRC_CHECK
    const uint16_t expect_crc = sd_crc16(sd_spi_context.sd_dma_context.len, sd_spi_context.sd_dma_context.read_buf);
    const uint16_t act_crc = sd_spi_context.sd_dma_context.crc_buf[0] << 8 | sd_spi_context.sd_dma_context.crc_buf[1];
    if (act_crc != expect_crc) {
#ifdef SD_DEBUG
        printf("read CRC fail: got %04hx, expected %04hx\n", act_crc, expect_crc);
#endif
        return false;
    }
#endif
    return true;
}

bool sd_cmd_write(uint8_t cmd, uint32_t arg, unsigned datalen, uint8_t data[const static datalen])
{
    uint8_t buf[2];
    const uint16_t crc = sd_crc16(datalen, data);
    sd_spi_cmd_send(cmd, arg);
    // Read up to 8 garbage bytes (0xff), followed by R1 (MSB is zero)
    bool got_r1 = false;
    for (int timeout = 0; timeout < 8; ++timeout) {
        sd_spi_read_blocking(0xff, buf, 1);
        if (!(buf[0] & 0x80)) {
            got_r1 = true;
            break;
        }
    }
    if (!got_r1 || buf[0] != 0x00)
        goto abort;
    buf[0] = 0xfe;
    sd_spi_write_blocking(buf, 1);
    sd_spi_write_blocking(data, datalen);
    buf[0] = crc >> 8;
    buf[1] = crc;
    sd_spi_write_blocking(buf, 2);
    sd_spi_read_blocking(0xff, buf, 1);
    if ((buf[0] & 0x1f) != 0x5) {
#ifdef SD_DEBUG
        printf("Write fail: %2hhx\n", buf[0]);
#endif
        goto abort;
    }

    int timeout = 0;
    bool got_done = false;
    for (timeout = 0; timeout < 131072; ++timeout) {
        sd_spi_read_blocking(0xff, buf, 1);
        if (buf[0] != 0x0) {
            got_done = true;
            break;
        }
    }
#ifdef SD_DEBUG
    printf("dbg write end: %d, %2hhx\n", timeout, buf[0]);
#endif
    if (!got_done)
        goto abort;

    gpio_put(sd_spi_context.ss, true);
    sd_spi_read_blocking(0xff, buf, 1);
    return true;

abort:
    gpio_put(sd_spi_context.ss, true);
    sd_spi_read_blocking(0xff, buf, 1);
    return false;
}

bool sd_spi_init(int mosi, int miso, int sck, int ss)
{
    if (sd_spi_context.initialized)
        return false;
    if (!pio_can_add_program(SD_PIO, &sd_spi_pio_program))
        return false;
    sd_spi_context.spi_sm = pio_claim_unused_sm(SD_PIO, false);
    if (sd_spi_context.spi_sm == -1)
        return false;
    sd_spi_context.spi_offset = pio_add_program(SD_PIO, &sd_spi_pio_program);
    sd_spi_context.mosi = mosi;
    sd_spi_context.miso = miso;
    sd_spi_context.sck = sck;
    sd_spi_context.ss = ss;
    sd_spi_pio_program_init(SD_PIO, sd_spi_context.spi_sm, sd_spi_context.spi_offset, sd_spi_context.mosi,
                            sd_spi_context.miso, sd_spi_context.sck, SD_INIT_BITRATE);
    pio_sm_set_enabled(SD_PIO, sd_spi_context.spi_sm, true);
    gpio_init(sd_spi_context.ss);
    gpio_set_dir(sd_spi_context.ss, true);

    sd_spi_context.spi_dma_rd = dma_claim_unused_channel(false);
    sd_spi_context.spi_dma_rd_crc = dma_claim_unused_channel(false);
    sd_spi_context.spi_dma_wr = dma_claim_unused_channel(false);
    if (sd_spi_context.spi_dma_rd == -1 || sd_spi_context.spi_dma_rd_crc == -1 || sd_spi_context.spi_dma_wr == -1)
        return false;
    sd_spi_context.spi_dma_rd_cfg = dma_channel_get_default_config(sd_spi_context.spi_dma_rd);
    channel_config_set_read_increment(&sd_spi_context.spi_dma_rd_cfg, false);
    channel_config_set_write_increment(&sd_spi_context.spi_dma_rd_cfg, true);
    channel_config_set_dreq(&sd_spi_context.spi_dma_rd_cfg, pio_get_dreq(SD_PIO, sd_spi_context.spi_sm, false));
    channel_config_set_transfer_data_size(&sd_spi_context.spi_dma_rd_cfg, DMA_SIZE_8);
    sd_spi_context.spi_dma_rd_crc_cfg = dma_channel_get_default_config(sd_spi_context.spi_dma_rd_crc);
    channel_config_set_read_increment(&sd_spi_context.spi_dma_rd_crc_cfg, false);
    channel_config_set_write_increment(&sd_spi_context.spi_dma_rd_crc_cfg, true);
    channel_config_set_dreq(&sd_spi_context.spi_dma_rd_crc_cfg, pio_get_dreq(SD_PIO, sd_spi_context.spi_sm, false));
    channel_config_set_transfer_data_size(&sd_spi_context.spi_dma_rd_crc_cfg, DMA_SIZE_8);
    sd_spi_context.spi_dma_wr_cfg = dma_channel_get_default_config(sd_spi_context.spi_dma_wr);
    channel_config_set_read_increment(&sd_spi_context.spi_dma_wr_cfg, false);
    channel_config_set_dreq(&sd_spi_context.spi_dma_wr_cfg, pio_get_dreq(SD_PIO, sd_spi_context.spi_sm, true));
    channel_config_set_transfer_data_size(&sd_spi_context.spi_dma_wr_cfg, DMA_SIZE_8);
    sd_spi_context.sd_dma_context.state = DMA_IDLE;
    irq_add_shared_handler(DMA_IRQ_0, &sd_spi_dma_isr, PICO_SHARED_IRQ_HANDLER_DEFAULT_ORDER_PRIORITY);
    dma_channel_set_irq0_enabled(sd_spi_context.spi_dma_rd, true);
    dma_channel_set_irq0_enabled(sd_spi_context.spi_dma_rd_crc, true);
    irq_set_enabled(DMA_IRQ_0, true);

    gpio_put(sd_spi_context.ss, true);
    uint8_t buf[16];
    memset(buf, 0xff, 16);
    // Ensure at least 74 SPI clock cycles without CS asserted

    sd_spi_write_blocking(buf, 10);
    sd_spi_context.initialized = true;
    return true;
}

bool sd_spi_deinit(void)
{
    if (!sd_spi_context.initialized)
        return false;
    if (sd_spi_context.sd_dma_context.state != DMA_IDLE)
        return false;
    dma_channel_set_irq0_enabled(sd_spi_context.spi_dma_rd, false);
    dma_channel_set_irq0_enabled(sd_spi_context.spi_dma_rd_crc, false);
    irq_remove_handler(DMA_IRQ_0, &sd_spi_dma_isr);
    dma_channel_unclaim(sd_spi_context.spi_dma_rd);
    dma_channel_unclaim(sd_spi_context.spi_dma_rd_crc);
    dma_channel_unclaim(sd_spi_context.spi_dma_wr);
    pio_remove_program(SD_PIO, &sd_spi_pio_program, sd_spi_context.spi_offset);
    pio_sm_unclaim(SD_PIO, sd_spi_context.spi_sm);

    sd_spi_context.initialized = false;
    return true;
}

void sd_spi_set_bitrate(const int rate)
{
    pio_sm_set_enabled(SD_PIO, sd_spi_context.spi_sm, false);
    sd_spi_pio_program_init(SD_PIO, sd_spi_context.spi_sm, sd_spi_context.spi_offset, sd_spi_context.mosi,
                            sd_spi_context.miso, sd_spi_context.sck, rate);
    pio_sm_set_enabled(SD_PIO, sd_spi_context.spi_sm, true);
}
