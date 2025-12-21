// SPDX-License-Identifier: MIT
// Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

#include "py/obj.h"
#include "py/runtime.h"
#include "py/objstr.h"

#ifndef TONBERRY_GIT_REVISION
#define TONBERRY_GIT_REVISION "unknown"
#endif
#ifndef TONBERRY_VERSION
#define TONBERRY_VERSION "unknown"
#endif

static const MP_DEFINE_STR_OBJ(tonberry_git_revision_obj, TONBERRY_GIT_REVISION);
static const MP_DEFINE_STR_OBJ(tonberry_version_obj, TONBERRY_VERSION);

static const mp_rom_map_elem_t board_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_board)},
    {MP_ROM_QSTR(MP_QSTR_revision), MP_ROM_PTR(&tonberry_git_revision_obj)},
    {MP_ROM_QSTR(MP_QSTR_version), MP_ROM_PTR(&tonberry_version_obj)},
};
static MP_DEFINE_CONST_DICT(board_module_globals, board_module_globals_table);

const mp_obj_module_t board_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&board_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR_board, board_cmodule);
