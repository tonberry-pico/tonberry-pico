// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2025 Matthias Blankertz <matthias@blankertz.org>

#include "audiocore.h"

// Include MicroPython API.
#include "py/mperrno.h"
#include "py/runtime.h"
#include "shared/runtime/mpirq.h"

// This module is RP2 specific
#include "mphalport.h"
#include <pico/platform/sections.h>

#include <string.h>

struct audiocore_shared_context shared_context = {.lock = NULL};
static bool initialized = false;

struct audiocore_obj {
    mp_obj_base_t base;
    mp_irq_obj_t *irq_obj;
    uint32_t fifo_read_value;
};
const mp_obj_type_t audiocore_type;

static struct audiocore_obj *the_audiocore_obj = NULL;

static void __time_critical_func(fifo_isr)(void)
{
    if (!multicore_fifo_rvalid())
        return;
    const uint32_t val = sio_hw->fifo_rd;
    if (!the_audiocore_obj)
        return;
    if (val & AUDIOCORE_FIFO_DATA_FLAG)
        the_audiocore_obj->fifo_read_value = val;
    if (the_audiocore_obj->irq_obj)
        mp_irq_handler(the_audiocore_obj->irq_obj);
}

static const mp_irq_methods_t audiocore_irq_methods = {};

// Poke core1 if it is currently waiting for an event (__wfe)
static __always_inline void wake_core1(void) { __sev(); }

static uint32_t get_fifo_read_value_blocking(struct audiocore_obj *obj)
{
    while (true) {
        const long flags = save_and_disable_interrupts();
        const uint32_t value = obj->fifo_read_value;
        obj->fifo_read_value = 0;
        if (value & AUDIOCORE_FIFO_DATA_FLAG) {
            restore_interrupts(flags);
            return value & ~AUDIOCORE_FIFO_DATA_FLAG;
        }
        __wfi();
        restore_interrupts(flags);
        __nop(); // Ensure at least two instructions between enable interrupts and subsequent disable
        __nop();
    }
}

/*
 * audiocore.Context.deinit(self)
 *
 * Deinitializes the audiocore.Context and shuts down processing on core1
 */
static mp_obj_t audiocore_deinit(mp_obj_t self_in)
{
    struct audiocore_obj *self = MP_OBJ_TO_PTR(self_in);
    multicore_fifo_push_blocking(AUDIOCORE_CMD_SHUTDOWN);
    get_fifo_read_value_blocking(self);
    irq_set_enabled(SIO_IRQ_PROC0, false);
    irq_remove_handler(SIO_IRQ_PROC0, &fifo_isr);
    the_audiocore_obj = NULL;
    initialized = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(audiocore_deinit_obj, audiocore_deinit);

/*
 * (copied, buf_space, undderuns) = audiocore.put(self, buffer)
 *
 * Copies as many bytes as possible from the buffer to the audiocore ring buffer for playback.
 * 'buffer' must be any object supporting the buffer protocol with data in byte (array typecode 'b' or 'B')
 * format. The actual number of elements copied is returned in 'copied', the remaining free buffer space
 * is in 'buf_space', and the total number of audio underruns since initialization of the audiocore Context
 * is in 'underruns'.
 */
static mp_obj_t audiocore_put(mp_obj_t self_in, mp_obj_t buffer)
{
    struct audiocore_obj *self = MP_OBJ_TO_PTR(self_in);
    (void)self;
    mp_buffer_info_t bufinfo;
    if (!mp_get_buffer(buffer, &bufinfo, MP_BUFFER_READ))
        mp_raise_ValueError(MP_ERROR_TEXT("not a read buffer"));
    if (bufinfo.typecode != 'b' && bufinfo.typecode != 'B')
        mp_raise_ValueError(MP_ERROR_TEXT("unsupported buffer type"));
    unsigned to_copy = bufinfo.len;

    const uint32_t flags = spin_lock_blocking(shared_context.lock);
    const unsigned buf_space = audiocore_get_buffer_space();
    if (to_copy > buf_space)
        to_copy = buf_space;
    if (to_copy > 0) {
        audiocore_buffer_put(bufinfo.buf, to_copy);
        wake_core1();
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
static MP_DEFINE_CONST_FUN_OBJ_2(audiocore_put_obj, audiocore_put);

/*
 * audiocore.flush(self)
 *
 * Tells the audiocore to stop playback as soon as all MP3 frames still in the buffer have been decoded.
 * This function blocks until playback has ended.
 */
static mp_obj_t audiocore_flush(mp_obj_t self_in)
{
    struct audiocore_obj *self = MP_OBJ_TO_PTR(self_in);
    multicore_fifo_push_blocking(AUDIOCORE_CMD_FLUSH);
    wake_core1();
    get_fifo_read_value_blocking(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(audiocore_flush_obj, audiocore_flush);

/*
 * audiocore.set_volume(self, volume)
 *
 * Set a volume between 0 (silence) and 255 (PCM values are output as they are decoded from the mp3 stream). Bewteen
 * 0 and 255 the volume is scaled linearly.
 * Raises a ValueError of the volume is not in the range [0, 255].
 * Raises an OSError if the audiocore rejects the volume setting.
 */
static mp_obj_t audiocore_set_volume(mp_obj_t self_in, mp_obj_t volume_obj)
{
    struct audiocore_obj *self = MP_OBJ_TO_PTR(self_in);
    const int volume = mp_obj_get_int(volume_obj);
    if (volume < 0 || volume > 255)
        mp_raise_ValueError(MP_ERROR_TEXT("volume out of range"));
    multicore_fifo_push_blocking(AUDIOCORE_CMD_SET_VOLUME);
    multicore_fifo_push_blocking(AUDIOCORE_MAX_VOLUME * volume / 255);
    wake_core1();
    const uint32_t ret = get_fifo_read_value_blocking(self);
    if (ret != 0)
        mp_raise_OSError(MP_EINVAL);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(audiocore_set_volume_obj, audiocore_set_volume);

/*
 * Audiocore(pin, sideset)
 *
 * Initialize the audiocore module, starting the audio processing on core1.
 * The pin parameter specifies the I2S data pin, the sideset parameter specifies the I2S LRCLK pin, the
 * BCLK must be on pin sideset+1.
 * Only a single Audiocore may exist at a time.
 * Constructs an Audiocore object on success, raises a OSError or ValueError on failure.
 */
static void audiocore_init(struct audiocore_obj *obj, size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args)
{
    enum { ARG_pin, ARG_sideset, ARG_handler };
    static const mp_arg_t allowed_args[] = {
        {MP_QSTR_pin, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL}},
        {MP_QSTR_sideset, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL}},
        {MP_QSTR_handler, MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL}},
    };
    if (initialized)
        mp_raise_OSError(MP_EBUSY);
    if (!shared_context.lock) {
        // initialize shared context lock on first init
        int lock = spin_lock_claim_unused(false);
        if (lock == -1)
            mp_raise_OSError(MP_ENOMEM);
        shared_context.lock = spin_lock_init(lock);
    }
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);
    const mp_hal_pin_obj_t pin = mp_hal_get_pin_obj(args[ARG_pin].u_obj);
    const mp_hal_pin_obj_t sideset_pin = mp_hal_get_pin_obj(args[ARG_sideset].u_obj);
    if (args[ARG_handler].u_obj != MP_OBJ_NULL) {
        obj->irq_obj = mp_irq_new(&audiocore_irq_methods, MP_OBJ_FROM_PTR(obj));
        obj->irq_obj->handler = args[ARG_handler].u_obj;
        obj->irq_obj->ishard = false;
    } else {
        obj->irq_obj = NULL;
    }
    the_audiocore_obj = obj;
    irq_set_exclusive_handler(SIO_IRQ_PROC0, &fifo_isr);
    irq_set_enabled(SIO_IRQ_PROC0, true);
    shared_context.mp3_buffer_write = shared_context.mp3_buffer_read = shared_context.underruns = 0;
    memset(shared_context.mp3_buffer, 0, MP3_BUFFER_PREAREA + MP3_BUFFER_SIZE);
    multicore_reset_core1();
    shared_context.out_pin = pin;
    shared_context.sideset_base = sideset_pin;
    initialized = true;
    multicore_launch_core1(&core1_main);
    uint32_t result = get_fifo_read_value_blocking(obj);
    if (result != 0) {
        multicore_reset_core1();
        irq_set_enabled(SIO_IRQ_PROC0, false);
        irq_remove_handler(SIO_IRQ_PROC0, &fifo_isr);
        the_audiocore_obj = NULL;
        initialized = false;
        mp_raise_OSError(result);
    }
}

static mp_obj_t audiocore_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    struct audiocore_obj *audiocore = mp_obj_malloc(struct audiocore_obj, &audiocore_type);
    mp_map_t kw_args;
    mp_map_init_fixed_table(&kw_args, n_kw, args + n_args);
    audiocore_init(audiocore, n_args, args, &kw_args);
    return MP_OBJ_FROM_PTR(audiocore);
}

static const mp_rom_map_elem_t audiocore_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&audiocore_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&audiocore_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_put), MP_ROM_PTR(&audiocore_put_obj)},
    {MP_ROM_QSTR(MP_QSTR_flush), MP_ROM_PTR(&audiocore_flush_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_volume), MP_ROM_PTR(&audiocore_set_volume_obj)},
};
static MP_DEFINE_CONST_DICT(audiocore_locals_dict, audiocore_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(audiocore_type, MP_QSTR_Audiocore, MP_TYPE_FLAG_NONE, locals_dict, &audiocore_locals_dict,
                         make_new, &audiocore_make_new);

static const mp_rom_map_elem_t audiocore_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR__audiocore)},
    {MP_ROM_QSTR(MP_QSTR_Audiocore), MP_ROM_PTR(&audiocore_type)},
};
static MP_DEFINE_CONST_DICT(audiocore_module_globals, audiocore_module_globals_table);

const mp_obj_module_t audiocore_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&audiocore_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR__audiocore, audiocore_cmodule);
