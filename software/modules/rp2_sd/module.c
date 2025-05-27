// SPDX-License-Identifier: MIT
// Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

#include "py/obj.h"
#include "sd.h"

// Include MicroPython API.
#include "py/mperrno.h"
#include "py/runtime.h"

// This module is RP2 specific
#include "mphalport.h"

#include <string.h>

const mp_obj_type_t sdcard_type;
struct sdcard_obj {
    mp_obj_base_t base;
    struct sd_context sd_context;
};

static void sdcard_init(struct sdcard_obj *obj, size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args)
{
    enum { ARG_mosi, ARG_miso, ARG_sck, ARG_ss, ARG_baudrate };
    static const mp_arg_t allowed_args[] = {
        {MP_QSTR_mosi, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL}},
        {MP_QSTR_miso, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL}},
        {MP_QSTR_sck, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL}},
        {MP_QSTR_ss, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL}},
        {MP_QSTR_baudrate, MP_ARG_INT, {.u_int = 15000000}},
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);
    const mp_hal_pin_obj_t pin_mosi = mp_hal_get_pin_obj(args[ARG_mosi].u_obj);
    const mp_hal_pin_obj_t pin_miso = mp_hal_get_pin_obj(args[ARG_miso].u_obj);
    const mp_hal_pin_obj_t pin_sck = mp_hal_get_pin_obj(args[ARG_sck].u_obj);
    const mp_hal_pin_obj_t pin_ss = mp_hal_get_pin_obj(args[ARG_ss].u_obj);
    const unsigned baudrate = args[ARG_baudrate].u_int;
    if (!sd_init(&obj->sd_context, pin_mosi, pin_miso, pin_sck, pin_ss, baudrate)) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("sd_init() failed"));
    }
}

static mp_obj_t sdcard_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    struct sdcard_obj *sdcard = mp_obj_malloc(struct sdcard_obj, &sdcard_type);
    mp_map_t kw_args;
    mp_map_init_fixed_table(&kw_args, n_kw, args + n_args);
    sdcard_init(sdcard, n_args, args, &kw_args);
    return MP_OBJ_FROM_PTR(sdcard);
}

static mp_obj_t sdcard_deinit(mp_obj_t self_obj)
{
    struct sdcard_obj *self = MP_OBJ_TO_PTR(self_obj);
    if (!sd_deinit(&self->sd_context))
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("sd_deinit() failed"));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sdcard_deinit_obj, sdcard_deinit);

static mp_obj_t sdcard_readblocks(mp_obj_t self_obj, mp_obj_t block_obj, mp_obj_t buf_obj)
{
    struct sdcard_obj *self = MP_OBJ_TO_PTR(self_obj);
    const int start_block = mp_obj_get_int(block_obj);
    mp_buffer_info_t bufinfo;
    if (!mp_get_buffer(buf_obj, &bufinfo, MP_BUFFER_WRITE))
        mp_raise_ValueError("Not a write buffer");
    if (bufinfo.len % SD_SECTOR_SIZE != 0)
        mp_raise_ValueError("Buffer length is invalid");
    const int nblocks = bufinfo.len / SD_SECTOR_SIZE;
    for (int block = 0; block < nblocks; block++) {
        // TODO: Implement CMD18 read multiple blocks
        if (!sd_readblock(&self->sd_context, start_block + block, bufinfo.buf + block * SD_SECTOR_SIZE))
            mp_raise_OSError(MP_EIO);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(sdcard_readblocks_obj, sdcard_readblocks);

static mp_obj_t sdcard_ioctl(mp_obj_t self_obj, mp_obj_t op_obj, mp_obj_t arg_obj)
{
    struct sdcard_obj *self = MP_OBJ_TO_PTR(self_obj);
    int op = mp_obj_get_int(op_obj);
    switch (op) {
    case 4:
        return mp_obj_new_int(self->sd_context.blocks);
    case 5:
        return mp_obj_new_int(SD_SECTOR_SIZE);
    default:
        return mp_const_none;
    }
};
static MP_DEFINE_CONST_FUN_OBJ_3(sdcard_ioctl_obj, sdcard_ioctl);

static const mp_rom_map_elem_t sdcard_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&sdcard_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&sdcard_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_ioctl), MP_ROM_PTR(&sdcard_ioctl_obj)},
    {MP_ROM_QSTR(MP_QSTR_readblocks), MP_ROM_PTR(&sdcard_readblocks_obj)},
};
static MP_DEFINE_CONST_DICT(sdcard_locals_dict, sdcard_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(sdcard_type, MP_QSTR_SDCard, MP_TYPE_FLAG_NONE, locals_dict, &sdcard_locals_dict, make_new,
                         &sdcard_make_new);

static const mp_rom_map_elem_t rp2_sd_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_rp2_sd)},
    {MP_ROM_QSTR(MP_QSTR_SDCard), MP_ROM_PTR(&sdcard_type)},
};
static MP_DEFINE_CONST_DICT(rp2_sd_module_globals, rp2_sd_module_globals_table);

const mp_obj_module_t rp2_sd_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&rp2_sd_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR_rp2_sd, rp2_sd_cmodule);
