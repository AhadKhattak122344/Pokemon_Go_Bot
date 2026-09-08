from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from .adb import Adb
from .health import wait_ready


def compose(config: dict[str, Any], *args: str) -> None:
    root = Path(__file__).resolve().parents[1]
    command = ["docker", "compose", "-f", str(root / "docker-compose.yml")]
    if config["profile"] == "nested-virt":
        command += ["-f", str(root / "docker-compose.kvm.yml")]
    subprocess.run([*command, *args], cwd=root, check=True,
                   env={**os.environ, "EMULATOR_GPU": config["profiles"][config["profile"]]["gpu"]})


def up(config: dict[str, Any], adb: Adb) -> None:
    compose(config, "up", "-d", "emulator")
    try:
        wait_ready(adb, config["emulator"]["boot_timeout_s"])
    except TimeoutError:
        compose(config, "restart", "emulator")
        wait_ready(adb, config["emulator"]["boot_timeout_s"])
