#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

struct sd_context {
    size_t blocks;
    bool initialized;
    bool old_card;
    bool sdhc_sdxc;
};

bool sd_init(struct sd_context *context, int mosi, int miso, int sck, int ss, int rate);
bool sd_deinit(struct sd_context *sd_context);

bool sd_readblock(struct sd_context *context, size_t sector_num, uint8_t buffer[static 512]);

bool sd_readblock_start(struct sd_context *context, size_t sector_num, uint8_t buffer[static 512]);
bool sd_readblock_complete(struct sd_context *context);
bool sd_readblock_is_complete(struct sd_context *context);
