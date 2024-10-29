#pragma once

#include <stdbool.h>
#include <stdint.h>

#define I2S_DMA_BUF_SIZE (1152)

bool i2s_init(int samplerate);

uint32_t *i2s_next_buf(void);
void i2s_commit_buf(uint32_t *buf);
