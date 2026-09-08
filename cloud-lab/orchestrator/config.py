from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml


def package_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z]\w*(?:\.[A-Za-z]\w*)+", value):
        raise ValueError(f"Invalid Android package: {value!r}")
    return value


def component(value: str, package: str | None = None) -> str:
    if not re.fullmatch(r"[A-Za-z]\w*(?:\.[A-Za-z]\w*)+/\.?[A-Za-z_$][\w.$]*", value):
        raise ValueError(f"Invalid Android component: {value!r}")
    if package and value.split('/')[0] != package:
        raise ValueError("Scenario component must belong to the configured app")
    return value


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError("Config must be a YAML mapping")
    package_name(data["app"]["package"])
    component(data["app"]["activity"], data["app"]["package"])
    if data['app'].get('ready_activity'):
        component(data['app']['ready_activity'], data['app']['package'])
    data["profile"] = os.getenv("LAB_PROFILE", data["profile"])
    if data["profile"] not in data["profiles"]:
        raise ValueError("Unknown emulator profile")
    if data["location"]["backend"] != "geo":
        raise ValueError("This emulator harness supports location.backend: geo")
    data["adb"]["server"] = os.getenv("ADB_SERVER_SOCKET", data["adb"]["server"])
    data["adb"]["serial"] = os.getenv("LAB_SERIAL", data["adb"]["serial"])
    data["artifacts"] = os.getenv("LAB_ARTIFACTS", data["artifacts"])
    return data
