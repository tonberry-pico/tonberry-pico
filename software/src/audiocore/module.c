// SPDX-License-Identifier: MIT
// Copyright (c) 2024 Matthias Blankertz <matthias@blankertz.org>

#include "audiocore.h"

// Include MicroPython API.
#include "py/mperrno.h"
#include "py/runtime.h"

// This module is RP2 specific
#include "mphalport.h"
#include <pico/platform/sections.h>

#include <string.h>

struct audiocore_shared_context shared_context = {.lock = NULL};
static bool initialized = false;

struct audiocore_Context_obj {
    mp_obj_base_t base;
};

/*
 * audiocore.Context.deinit(self)
 *
 * Deinitializes the audiocore.Context and shuts down processing on core1
 */
static mp_obj_t audiocore_Context_deinit(mp_obj_t self_in)
{
    struct audiocore_Context_obj *self = MP_OBJ_TO_PTR(self_in);
    multicore_fifo_push_blocking(AUDIOCORE_CMD_SHUTDOWN);
    multicore_fifo_pop_blocking();
    (void)self;
    initialized = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(audiocore_Context_deinit_obj, audiocore_Context_deinit);

/*
 * (copied, buf_space, undderuns) = audiocore.Context.put(self, buffer)
 *
 * Copies as many integers as possible from the buffer to the audiocore ring buffer for playback.
 * 'buffer' must be any object supporting the buffer protocol with data in unsigned int (array typecode 'I')
 * format. The actual number of elements copied is returned in 'copied', the remaining free ring buffer space
 * is in 'buf_space', and the total number of buffer underruns since initialization of the audiocore Context
 * is in 'underruns'.
 */
static mp_obj_t audiocore_Context_put(mp_obj_t self_in, mp_obj_t buffer)
{
    struct audiocore_Context_obj *self = MP_OBJ_TO_PTR(self_in);
    (void)self;
    mp_buffer_info_t bufinfo;
    if (!mp_get_buffer(buffer, &bufinfo, MP_BUFFER_READ))
        mp_raise_ValueError("not a read buffer");
    if (bufinfo.typecode != 'I')
        mp_raise_ValueError("unsupported buffer type");
    unsigned to_copy = bufinfo.len / 4;

    const uint32_t flags = spin_lock_blocking(shared_context.lock);
    const unsigned buf_space = audiocore_get_audio_buffer_space();
    if (to_copy > buf_space)
        to_copy = buf_space;
    if (to_copy > 0) {
        audiocore_audio_buffer_put(bufinfo.buf, to_copy);
    }
    const unsigned underruns = shared_context.underruns;
    spin_unlock(shared_context.lock, flags);

    mp_obj_t items[] = {
        mp_obj_new_int(to_copy),
        mp_obj_new_int(buf_space),
        mp_obj_new_int(underruns),
    };
    return mp_obj_new_tuple(3, items);
}
static MP_DEFINE_CONST_FUN_OBJ_2(audiocore_Context_put_obj, audiocore_Context_put);

static uint32_t __scratch_y("core1_stack") core1_stack[1024];
static const mp_rom_map_elem_t audiocore_Context_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&audiocore_Context_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&audiocore_Context_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_put), MP_ROM_PTR(&audiocore_Context_put_obj)},
};
static MP_DEFINE_CONST_DICT(audiocore_Context_locals_dict, audiocore_Context_locals_dict_table);
const mp_obj_type_t audiocore_Context_type;

MP_DEFINE_CONST_OBJ_TYPE(audiocore_Context_type, MP_QSTR_Context, MP_TYPE_FLAG_NONE, locals_dict,
                         &audiocore_Context_locals_dict);

/*
 * audiocore.init(pin, sideset, samplerate)
 * Returns: audiocore.Context
 *
 * Initialize the audiocore module, starting the audio processing on core1 and initializing the I2S driver.
 * The pin parameter specifies the I2S data pin, the sideset parameter specifies the I2S LRCLK pin, the
 * BCLK must be on pin sideset+1.
 * Samplerate should be 44100 or 48000.
 * Only a single audiocore.Context may exist at a time.
 * Return a audiocore.Context object on success, raises a OSError or ValueError on failure.
 */
static mp_obj_t audiocore_init(mp_obj_t pin_obj, mp_obj_t sideset_obj, mp_obj_t samplerate_obj)
{
    if (initialized)
        mp_raise_OSError(MP_EBUSY);
    if (!shared_context.lock) {
        // initialize shared context lock on first init
        int lock = spin_lock_claim_unused(false);
        if (lock == -1)
            mp_raise_OSError(MP_ENOMEM);
        shared_context.lock = spin_lock_init(lock);
    }
    shared_context.audio_buffer_write = shared_context.audio_buffer_read = shared_context.underruns = 0;
    memset(shared_context.audio_buffer, 0, AUDIO_BUFFER_SIZE * 4);
    multicore_reset_core1();
    struct audiocore_Context_obj *context = m_malloc_with_finaliser(sizeof(struct audiocore_Context_obj));
    context->base.type = &audiocore_Context_type;
    mp_hal_pin_obj_t pin = pin_obj == MP_OBJ_NULL ? -1 : mp_hal_get_pin_obj(pin_obj);
    if (pin == -1)
        mp_raise_ValueError("Invalid out pin");
    mp_hal_pin_obj_t sideset_pin = sideset_obj == MP_OBJ_NULL ? -1 : mp_hal_get_pin_obj(sideset_obj);
    if (sideset_pin == -1)
        mp_raise_ValueError("Invalid sideset base pin");
    int samplerate = mp_obj_get_int(samplerate_obj);
    shared_context.out_pin = pin;
    shared_context.sideset_base = sideset_pin;
    shared_context.samplerate = samplerate;
    initialized = true;
    multicore_launch_core1_with_stack(&core1_main, core1_stack, sizeof(core1_stack));
    uint32_t result = multicore_fifo_pop_blocking();
    if (result != 0) {
        multicore_reset_core1();
        initialized = false;
        mp_raise_OSError(result);
    }

    return MP_OBJ_FROM_PTR(context);
}
static MP_DEFINE_CONST_FUN_OBJ_3(audiocore_init_obj, audiocore_init);

static const mp_rom_map_elem_t audiocore_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_audiocore)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&audiocore_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_Context), MP_ROM_PTR(&audiocore_Context_type)},
};
static MP_DEFINE_CONST_DICT(audiocore_module_globals, audiocore_module_globals_table);

const mp_obj_module_t audiocore_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&audiocore_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR_audiocore, audiocore_cmodule);
