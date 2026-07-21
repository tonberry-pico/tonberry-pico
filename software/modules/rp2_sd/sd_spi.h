#pragma once

#include <stdbool.h>
#include <stdint.h>

#define SD_MISO 4
#define SD_SCK 2
#define SD_MOSI 3
#define SD_CS 5

#define SD_PIO pio0

#define SD_INIT_BITRATE 400000
#define SD_BITRATE 15000000

bool sd_cmd(const uint8_t cmd, const uint32_t arg, unsigned resplen, uint8_t resp[static resplen]);
bool sd_cmd_read(uint8_t cmd, uint32_t arg, unsigned datalen, uint8_t data[static datalen]);

bool sd_spi_init(int mosi, int miso, int sck, int ss);
bool sd_spi_deinit(void);
void sd_spi_set_bitrate(const int rate);

void sd_spi_dbg_clk(const int div, const int frac);

bool sd_cmd_read_start(uint8_t cmd, uint32_t arg, unsigned datalen, uint8_t data[static datalen]);
bool sd_cmd_read_complete(void);
bool sd_cmd_read_is_complete(void);

bool sd_cmd_write(uint8_t cmd, uint32_t arg, unsigned datalen, uint8_t data[const static datalen]);
bool sd_cmd_write_multiple(uint8_t cmd, uint32_t arg, unsigned blocks, unsigned datalen, uint8_t *const data);
