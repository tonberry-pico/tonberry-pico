#pragma once

#include <stddef.h>
#include <stdint.h>

inline static uint8_t sd_crc7(size_t len, const uint8_t data[const static len])
{
    const uint8_t poly = 0b1001;
    uint8_t crc = 0;
    for (size_t pos = 0; pos < len; ++pos) {
        crc ^= data[pos];
        for (int bit = 0; bit < 8; ++bit) {
            crc = (crc << 1) ^ ((crc & 0x80) ? (poly << 1) : 0);
        }
    }
    return crc >> 1;
}

/* inline static uint16_t sd_crc16(size_t len, const uint8_t data[const static len]) */
/* { */
/*     const uint16_t poly = 0b1000000100001; */
/*     uint16_t crc = 0; */
/*     for (size_t pos = 0; pos < len; ++pos) { */
/*         crc ^= data[pos] << 8; */
/*         for (int bit = 0; bit < 8; ++bit) { */
/*             crc = (crc << 1) ^ ((crc & 0x8000) ? poly : 0); */
/*         } */
/*     } */
/*     return crc; */
/* } */
