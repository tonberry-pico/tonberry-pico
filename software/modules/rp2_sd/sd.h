#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define SD_SECTOR_SIZE 512

struct sd_context {
    size_t blocks;
    size_t blocksize;
    bool initialized;
    bool old_card;
    bool sdhc_sdxc;
};

bool sd_init(struct sd_context *context, int mosi, int miso, int sck, int ss, int rate);
bool sd_deinit(struct sd_context *sd_context);

bool sd_readblock(struct sd_context *context, size_t sector_num, uint8_t buffer[static SD_SECTOR_SIZE]);

bool sd_readblock_start(struct sd_context *context, size_t sector_num, uint8_t buffer[static SD_SECTOR_SIZE]);
bool sd_readblock_complete(struct sd_context *context);
bool sd_readblock_is_complete(struct sd_context *context);

bool sd_writeblock(struct sd_context *context, size_t sector_num, uint8_t buffer[const static SD_SECTOR_SIZE]);
