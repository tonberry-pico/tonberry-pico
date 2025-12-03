# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

from errno import ENOENT
import json
import os
try:
    from typing import TYPE_CHECKING, Mapping, Any
except ImportError:
    TYPE_CHECKING = False


class Configuration:
    DEFAULT_CONFIG = {
        'LED_COUNT': 1,
        'IDLE_TIMEOUT_SECS': 60,
        'TAG_TIMEOUT_SECS': 5,
        'BUTTON_MAP': {
            'PLAY_PAUSE': 4,
            'VOLUP': 0,
            'VOLDOWN': 2,
            'PREV': None,
            'NEXT': 1,
        }
    }

    def __init__(self, config_path='/config.json'):
        self.config_path = config_path
        try:
            with open(self.config_path, 'r') as conf_file:
                self.config = json.load(conf_file)
        except OSError as ex:
            if ex.errno == ENOENT:
                self.config = Configuration.DEFAULT_CONFIG
                self._save()
            else:
                raise
        except ValueError as ex:
            print(f"Warning: Could not load configuration {self.config_path}:\n{ex}")
            self._move_config_to_backup()
            self.config = Configuration.DEFAULT_CONFIG

    def _move_config_to_backup(self):
        # Remove old backup
        try:
            os.remove(self.config_path + '.bup')
            os.rename(self.config_path, self.config_path + '.bup')
        except OSError as ex:
            if ex.errno != ENOENT:
                raise
        os.sync()

    def _save(self):
        with open(self.config_path + '.new', 'w') as conf_file:
            json.dump(self.config, conf_file)
        self._move_config_to_backup()
        os.rename(self.config_path + '.new', self.config_path)
        os.sync()

    def _get(self, key):
        return self.config.get(key, self.DEFAULT_CONFIG[key])

    def get_led_count(self) -> int:
        return self._get('LED_COUNT')

    def get_idle_timeout(self) -> int:
        return self._get('IDLE_TIMEOUT_SECS')

    def get_tag_timeout(self) -> int:
        return self._get('TAG_TIMEOUT_SECS')

    def get_button_map(self) -> Mapping[str, int | None]:
        return self._get('BUTTON_MAP')

    # For the web API
    def get_config(self) -> Mapping[str, Any]:
        return self.config

    def _validate(self, default, config, path=''):
        for k in config.keys():
            if k not in default:
                raise ValueError(f'Invalid config key {path}/{k}')
            if isinstance(default[k], dict):
                if not isinstance(config[k], dict):
                    raise ValueError(f'Invalid config: Value of {path}/{k} must be mapping')
                self._validate(default[k], config[k], f'{path}/{k}')

    def set_config(self, config):
        self._validate(self.DEFAULT_CONFIG, config)
        self.config = config
        self._save()
