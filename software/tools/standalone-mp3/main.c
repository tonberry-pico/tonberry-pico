#include "i2s.h"
#include "sd.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#include <hardware/clocks.h>
#include <hardware/gpio.h>
#include <hardware/spi.h>
#include <hardware/sync.h>
#include <pico/stdio.h>
#include <pico/stdlib.h>
#include <pico/time.h>

#include "mp3dec.h"
#include "sd_spi.h"

extern void sd_spi_dbg_clk(const int div, const int frac);

extern void sd_spi_dbg_loop(void);

#define MAX_VOLUME 0x8000u

void __time_critical_func(volume_adjust)(int16_t *restrict buf, size_t samples, uint16_t scalef)
{
    for (size_t pos = 0; pos < samples; ++pos) {
        buf[pos] = ((int32_t)buf[pos] * scalef) >> 15;
    }
}

static int __time_critical_func(play_mp3)(struct sd_context *sd_context)
{
    HMP3Decoder mp3dec = MP3InitDecoder();

    if (!i2s_init(44100)) {
        return 1;
    }

    uint8_t mp3buffer[4 * 512];
    for (int i = 0; i < sizeof(mp3buffer) / 512; ++i) {
        sd_readblock(sd_context, i, mp3buffer + 512 * i);
    }
    size_t next_sector = sizeof(mp3buffer) / 512;

    unsigned char *readptr = mp3buffer;
    int bytes_left = sizeof(mp3buffer);

    bool first = true;
    bool pending_read = false;
    bool synced = false;
    while (true) {
        /* Get some input data */
        if (pending_read && sd_readblock_is_complete(sd_context)) {
            sd_readblock_complete(sd_context);
            bytes_left += 512;
            pending_read = false;
        }
        if (!pending_read && (sizeof(mp3buffer) - bytes_left >= 512)) {
            // If there is not enough space for an mp3 frame, or if there is less than one SD block to the end, move
            // remaining data to start of buffer
            if (readptr - mp3buffer >= sizeof(mp3buffer) - 1044 ||
                readptr - mp3buffer > sizeof(mp3buffer) - 512 - bytes_left) {
                memmove(mp3buffer, readptr, bytes_left);
                readptr = mp3buffer;
            }
            sd_readblock_start(sd_context, next_sector++, readptr + bytes_left);
            pending_read = true;
        }
        if (bytes_left == 0) {
            // Can't do anything without input, wait and try again
            __wfe();
            continue;
        }

        // Synchronize MP3 stream if neccessary
        if (!synced) {
            const int ofs = MP3FindSyncWord(readptr, bytes_left);
            if (ofs == -1) {
                printf("MP3 sync word not found\n");
                readptr += bytes_left;
                bytes_left = 0;
                continue; // try again
            }
            readptr += ofs;
            bytes_left -= ofs;
            printf("MP3 sync word found after %zu bytes\n", ofs);
            synced = true;
        }

        // Get an output buffer
        uint32_t *const buf = i2s_next_buf();
        if (!buf) {
            // No output needed, wait and try again
            __wfe();
            continue;
        }

        // Decode one frame
        unsigned char *const old_readptr = readptr;
        const int old_bytes_left = bytes_left;
        const int status = MP3Decode(mp3dec, &readptr, &bytes_left, (short *)buf, 0);
        if (status) {
            if (status == ERR_MP3_INDATA_UNDERFLOW) {
                readptr = old_readptr;
                bytes_left = old_bytes_left;
                printf("INDATA_UNDERFLOW\n");
                sd_readblock_complete(sd_context);
                continue;
            } else /*if (status== ERR_MP3_MAINDATA_UNDERFLOW)*/ {
                --bytes_left;
                ++readptr;
                synced = false;
                continue;
            }
            printf("MP3Decode failed: %d\n", status);
            break;
        }

        MP3FrameInfo info;
        MP3GetLastFrameInfo(mp3dec, &info);
        if (first) {
            printf("bitrate %d, nChans %d, samprate %d, bitsPerSample %d, outputSamps %d, layer %d, version %d\n",
                   info.bitrate, info.nChans, info.samprate, info.bitsPerSample, info.outputSamps, info.layer,
                   info.version);
            first = false;
        }
        if (info.outputSamps != 2304) {
            printf("Unexpected number of output samples: %d\n", info.outputSamps);
            return 1;
        }
        volume_adjust((int16_t *)buf, info.outputSamps, MAX_VOLUME >> 4);

        i2s_commit_buf(buf);
    }
}

static void write_test(struct sd_context *sd_context)
{
    uint8_t data_buffer[4096];
    do {
        for (int i = 0; i < sizeof(data_buffer) / SD_SECTOR_SIZE; ++i) {
            if (!sd_readblock(sd_context, i, data_buffer + SD_SECTOR_SIZE * i)) {
                printf("sd_readblock(%d) failed\n", i);
                return;
            }
        }

        for (int line = 0; line < 32; ++line) {
            printf("%04hx ", line * 16);
            for (int item = 0; item < 16; ++item) {
                printf("%02hhx%c", data_buffer[line * 16 + item], (item == 15) ? '\n' : ' ');
            }
        }

        for (int i = 0; i < SD_SECTOR_SIZE; ++i) {
            data_buffer[i] ^= 0xff;
        }

        if(!sd_writeblock(sd_context, 0, data_buffer)) {
            printf("sd_writeblock failed\n");
            return;
        }
        sleep_ms(1000);
    } while (data_buffer[SD_SECTOR_SIZE - 1] != 0xAA);
}

int main()
{
    stdio_init_all();
    printf("sysclk is %d Hz\n", clock_get_hz(clk_sys));

    struct sd_context sd_context;

    if (!sd_init(&sd_context, 3, 4, 2, 5, 15000000)) {
        return 1;
    }

#ifdef WRITE_TEST
    write_test(&sd_context);
#endif

#ifdef PLAY_TEST
    play_mp3(&sd_context);
#endif

    printf("Done.\n");
}
