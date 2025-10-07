#include "sd.h"
#include "sd_spi.h"
#include "sd_util.h"

#include <inttypes.h>
#include <stdio.h>
#include <string.h>

// #define SD_DEBUG

#define SD_R1_ILLEGAL_COMMAND (1 << 2)

static bool sd_acmd(const uint8_t cmd, const uint32_t arg, unsigned resplen, uint8_t res[static resplen])
{
    if (!sd_cmd(55, 0, 1, res))
        return false;
    if ((res[0] & 0x7e) != 0x00)
        return false;

    return sd_cmd(cmd, arg, resplen, res);
}

static bool sd_early_init(void)
{
    uint8_t buf;
    for (int i = 0; i < 5; ++i) {
        if (sd_cmd(0, 0, 1, &buf)) {
#ifdef SD_DEBUG
            printf("CMD0 resp %02hhx\n", buf);
#endif
            if (buf == 0x01) {
                return true;
            }
        }
#ifdef SD_DEBUG
        printf("CMD0 timeout, try again...\n");
#endif
    }
    return false;
}

static bool sd_check_interface_condition(void)
{
    uint8_t buf[5];
    if (sd_cmd(8, 0x000001AA, 5, buf)) {
        if ((buf[3] & 0xf) != 0x1 || buf[4] != 0xAA) {
            printf("sd_init: check interface condition failed\n");
            return false;
        }
    } else {
        if (buf[0] & SD_R1_ILLEGAL_COMMAND) {
            printf("sd_init: check interface condition returned illegal command - old card?\n");
        } else {
            printf("sd_init: check interface condition failed\n");
            return false;
        }
    }

    return true;
}

static bool sd_send_op_cond(void)
{
    uint8_t buf;
    bool use_acmd = true;
    for (int timeout = 0; timeout < 500; ++timeout) {
        bool result = false;
        if (use_acmd)
            result = sd_acmd(41, 0x40000000, 1, &buf);
        else
            result = sd_cmd(1, 0x40000000, 1, &buf);
        if (!result) {
            if (use_acmd && buf & SD_R1_ILLEGAL_COMMAND) {
#ifdef SD_DEBUG
                printf("sd_init: card does not understand ACMD41, try CMD1...\n");
#endif
                use_acmd = false;
                continue;
            } else if (buf != 0x01) {
                printf("sd_init: send_op_cond failed\n");
                return false;
            } else {
                continue;
            }
        }
        if (buf == 0x00) {
            return true;
        }
    }
    printf("sd_init: send_op_cond: timeout waiting for !idle\n");
    return false;
}

static bool sd_read_ocr(uint32_t *const ocr)
{
    uint8_t buf[5];
    if (!sd_cmd(58, 0, 5, buf))
        return false;
    *ocr = buf[1] << 24 | buf[2] << 16 | buf[3] << 8 | buf[4];
    return true;
}

static void sd_dump_cid [[maybe_unused]] (void)
{
    uint8_t buf[16];
    if (sd_cmd_read(10, 0, 16, buf)) {
        const uint8_t crc = sd_crc7(15, buf);
        const uint8_t card_crc = buf[15] >> 1;
        if (card_crc != crc) {
            printf("CRC mismatch: Got %02hhx, expected %02hhx\n", card_crc, crc);
            // Some cheap SD cards always report CRC=0, don't fail in that case
            if (card_crc != 0) {
                return;
            }
        }

        uint8_t mid = buf[0];
        char oid[2], pnm[5];
        memcpy(oid, buf + 1, 2);
        memcpy(pnm, buf + 3, 5);
        uint8_t prv = buf[8];
        uint32_t psn = buf[9] << 24 | buf[10] << 16 | buf[11] << 8 | buf[12];
        int mdt_year = 2000 + ((buf[13] & 0xf) << 4 | (buf[14] & 0xf0) >> 4);
        int mdt_month = buf[14] & 0x0f;
        printf("CID: mid: %02hhx, oid: %.2s, pnm: %.5s, prv: %02hhx, psn: %08" PRIx32 ", mdt_year: %d, mdt_month: %d\n",
               mid, oid, pnm, prv, psn, mdt_year, mdt_month);
    }
}

static bool sd_read_csd(struct sd_context *sd_context)
{
    uint8_t buf[16];
    if (sd_cmd_read(9, 0, 16, buf)) {
        const uint8_t crc = sd_crc7(15, buf);
        const uint8_t card_crc = buf[15] >> 1;
        if (card_crc != crc) {
            printf("CRC mismatch: Got %02hhx, expected %02hhx\n", card_crc, crc);
            // Some cheap SD cards always report CRC=0, don't fail in that case
            if (card_crc != 0) {
                return false;
            }
        }
        const unsigned csd_ver = buf[0] >> 6;
        unsigned blocksize [[maybe_unused]] = 0;
        unsigned blocks = 0;
        unsigned version [[maybe_unused]] = 0;
        switch (csd_ver) {
        case 0: {
            if (sd_context->sdhc_sdxc) {
                printf("sd_init: Got CSD v1.0 but card is SDHC/SDXC?\n");
                return false;
            }
            const unsigned read_bl_len = buf[5] & 0xf;
            if (read_bl_len < 9 || read_bl_len > 11) {
                printf("Invalid read_bl_len in CSD 1.0\n");
                return false;
            }
            blocksize = 1 << (buf[5] & 0xf);
            const unsigned c_size_mult = (buf[9] & 0x1) << 2 | (buf[10] & 0xc0) >> 6;
            const unsigned c_size = (buf[6] & 0x3) << 10 | (buf[7] << 2) | (buf[8] & 0xc0) >> 6;
            blocks = (c_size + 1) * (1 << (c_size_mult + 2));
            version = 1;
            break;
        }
        case 1: {
            blocksize = SD_SECTOR_SIZE;
            const unsigned c_size = (buf[7] & 0x3f) << 16 | buf[8] << 8 | buf[9];
            blocks = (c_size + 1) * 1024;
            version = 2;
            break;
        }
        case 2: {
            printf("sd_init: Got CSD v3.0, but SDUC does not support SPI.\n");
            return false;
        }
        }
        sd_context->blocks = blocks;
        sd_context->blocksize = blocksize;
#ifdef SD_DEBUG
        printf("CSD version %u.0, blocksize %u, blocks %u, capacity %llu MiB\n", version, blocksize, blocks,
               ((uint64_t)blocksize * blocks) / (1024 * 1024));
#endif
    }
    return true;
}

bool sd_init(struct sd_context *sd_context, int mosi, int miso, int sck, int ss, int rate)
{
    if (!sd_spi_init(mosi, miso, sck, ss)) {
        return false;
    }

    if (!sd_early_init()) {
        return false;
    }

    if (!sd_check_interface_condition()) {
        return false;
    }

    uint32_t ocr;
    if (!sd_read_ocr(&ocr)) {
        printf("sd_init: read OCR failed\n");
        return false;
    }
    if ((ocr & 0x00380000) != 0x00380000) {
        printf("sd_init: unsupported card voltage range\n");
        return false;
    }

    if (!sd_send_op_cond())
        return false;

    sd_spi_set_bitrate(rate);

    if (!sd_read_ocr(&ocr)) {
        printf("sd_init: read OCR failed\n");
        return false;
    }
    if (!(ocr & (1 << 31))) {
        printf("sd_init: card not powered up but !idle?\n");
        return false;
    }
    sd_context->sdhc_sdxc = (ocr & (1 << 30));

    if (!sd_read_csd(sd_context)) {
        return false;
    }

    if (sd_context->blocksize != SD_SECTOR_SIZE) {
        if (sd_context->blocksize != 1024 && sd_context->blocksize != 2048) {
            printf("sd_init: Unsupported block size %u\n", sd_context->blocksize);
            return false;
        }
        // Attempt SET_BLOCKLEN command
        uint8_t resp[1];
        if (!sd_cmd(16, SD_SECTOR_SIZE, 1, resp)) {
            printf("sd_init: SET_BLOCKLEN failed\n");
            return false;
        }
        // Successfully set blocksize to SD_SECTOR_SIZE, adjust context
        sd_context->blocks *= sd_context->blocksize / SD_SECTOR_SIZE;
#ifdef SD_DEBUG
        printf("Adjusted blocksize from %u to 512, card now has %u blocks\n", sd_context->blocksize,
               sd_context->blocks);
#endif
        sd_context->blocksize = SD_SECTOR_SIZE;
    }

#ifdef SD_DEBUG
    sd_dump_cid();
#endif

    sd_context->initialized = true;
    return true;
}

bool sd_deinit(struct sd_context *sd_context)
{
    if (!sd_spi_deinit())
        return false;
    sd_context->initialized = false;
    return true;
}

bool sd_readblock(struct sd_context *sd_context, size_t sector_num, uint8_t buffer[static SD_SECTOR_SIZE])
{
    if (!sd_context->initialized || sector_num >= sd_context->blocks)
        return false;

    uint32_t addr = sector_num;
    if (!sd_context->sdhc_sdxc) {
        // SDSC cards used byte addressing
        addr *= SD_SECTOR_SIZE;
    }
    return sd_cmd_read(17, addr, SD_SECTOR_SIZE, buffer);
}

bool sd_readblock_start(struct sd_context *sd_context, size_t sector_num, uint8_t buffer[static SD_SECTOR_SIZE])
{
    if (!sd_context->initialized || sector_num >= sd_context->blocks)
        return false;
    uint32_t addr = sector_num;
    if (!sd_context->sdhc_sdxc) {
        // SDSC cards used byte addressing
        addr *= SD_SECTOR_SIZE;
    }
    return sd_cmd_read_start(17, addr, SD_SECTOR_SIZE, buffer);
}

bool sd_readblock_complete(struct sd_context *sd_context)
{
    if (!sd_context->initialized)
        return false;
    sd_cmd_read_complete();
    return true;
}

bool sd_readblock_is_complete(struct sd_context *sd_context) { return sd_cmd_read_is_complete(); }

bool sd_writeblock(struct sd_context *sd_context, size_t sector_num, uint8_t buffer[const static SD_SECTOR_SIZE])
{
    if (!sd_context->initialized || sector_num >= sd_context->blocks)
        return false;

    uint32_t addr = sector_num;
    if (!sd_context->sdhc_sdxc) {
        // SDSC cards used byte addressing
        addr *= SD_SECTOR_SIZE;
    }
    return sd_cmd_write(24, addr, SD_SECTOR_SIZE, buffer);
}
