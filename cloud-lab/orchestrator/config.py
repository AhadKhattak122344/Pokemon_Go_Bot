from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Any

import yaml


def package_name(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z]\w*(?:\.[A-Za-z]\w*)+", value, re.ASCII):
        raise ValueError(f"Invalid Android package: {value!r}")
    return value


def component(value: str, package: str | None = None) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z]\w*(?:\.[A-Za-z]\w*)+/\.?[A-Za-z_$][\w.$]*", value, re.ASCII):
        raise ValueError(f"Invalid Android component: {value!r}")
    if package and value.split('/')[0] != package:
        raise ValueError("Scenario component must belong to the configured app")
    return value


def default_path() -> Path:
    source_config = Path(__file__).resolve().parents[1] / 'config' / 'default.yaml'
    return source_config if source_config.is_file() else Path(__file__).with_name('default.yaml')


def positive_number(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be a positive finite number')


def load(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise ValueError(f'Invalid YAML configuration: {exc}') from exc
    if not isinstance(data, dict):
        raise ValueError("Config must be a YAML mapping")
    for name in ('app', 'adb', 'emulator', 'profiles', 'location'):
        if not isinstance(data.get(name), dict):
            raise ValueError(f'{name} must be a YAML mapping')
    required = {'app': ('package', 'activity'), 'adb': ('executable', 'serial', 'server', 'timeout_s'),
                'emulator': ('api', 'avd', 'boot_timeout_s'), 'location': ('backend',)}
    for section, keys in required.items():
        for key in keys:
            if key not in data[section]:
                raise ValueError(f'Missing configuration field: {section}.{key}')
    package_name(data["app"]["package"])
    component(data["app"]["activity"], data["app"]["package"])
    if data['app'].get('ready_activity') is not None:
        component(data['app']['ready_activity'], data['app']['package'])
    for unsupported in ('instrumentation', 'reset_app_data', 'permissions'):
        if data['app'].get(unsupported):
            raise ValueError(f'app.{unsupported} is not implemented by the launch smoke test')
    data["profile"] = os.getenv("LAB_PROFILE", data.get("profile", ''))
    if not isinstance(data['profile'], str) or data["profile"] not in data["profiles"]:
        raise ValueError("Unknown emulator profile")
    profile = data['profiles'][data['profile']]
    if not isinstance(profile, dict) or profile.get('accel') not in ('on', 'off'):
        raise ValueError('Profile accel must be on or off (quoted in YAML)')
    if not isinstance(profile.get('gpu'), str) or not profile['gpu'].strip():
        raise ValueError('Profile gpu must be a nonempty string')
    if data["location"]["backend"] != "geo":
        raise ValueError("This emulator harness supports location.backend: geo")
    data["adb"]["server"] = os.getenv("ADB_SERVER_SOCKET", data["adb"]["server"])
    data["adb"]["serial"] = os.getenv("LAB_SERIAL", data["adb"]["serial"])
    data["artifacts"] = os.getenv("LAB_ARTIFACTS", data.get("artifacts", 'artifacts'))
    for section, key in (('adb', 'executable'), ('adb', 'server'), ('adb', 'serial'), ('emulator', 'avd')):
        if not isinstance(data[section][key], str) or not data[section][key].strip():
            raise ValueError(f'{section}.{key} must be a nonempty string')
    if not isinstance(data['artifacts'], str) or not data['artifacts'].strip():
        raise ValueError('artifacts must be a nonempty path string')
    positive_number(data['adb']['timeout_s'], 'adb.timeout_s')
    positive_number(data['emulator']['boot_timeout_s'], 'emulator.boot_timeout_s')
    api = data['emulator']['api']
    if isinstance(api, bool) or not isinstance(api, int) or api <= 0:
        raise ValueError('emulator.api must be a positive integer')
    return data
