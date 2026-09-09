from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path
from typing import Any

from .adb import Adb
from .health import wait_ready


def compose(config: dict[str, Any], *args: str) -> None:
    root = Path(__file__).resolve().parents[1]
    docker = root / 'config' / 'docker'
    if not (docker / 'docker-compose.yml').is_file():
        raise RuntimeError('Docker lifecycle commands require a source checkout; use --config for device commands')
    if args and args[0] != 'down' and (config['emulator']['api'] != 34 or config['emulator']['avd'] != 'baseline'):
        raise ValueError('The bundled Docker image supports emulator.api: 34 and emulator.avd: baseline only')
    profile = config['profiles'][config['profile']]
    command = ["docker", "compose", "-f", str(docker / "docker-compose.yml")]
    if profile['accel'] == 'on':
        command += ["-f", str(docker / "docker-compose.kvm.yml")]
    try:
        subprocess.run([*command, *args], cwd=root, check=True,
                   timeout=math.ceil(config['emulator']['boot_timeout_s']) * 2 + 180,
                   env={**os.environ, 'EMULATOR_GPU': profile['gpu'],
                        'EMULATOR_ACCEL': profile['accel'],
                        'BOOT_TIMEOUT': str(math.ceil(config['emulator']['boot_timeout_s'])),
                        'BOOT_HEALTH_START_PERIOD': str(math.ceil(config['emulator']['boot_timeout_s']) * 2 + 60) + 's'})
    except FileNotFoundError as exc:
        raise FileNotFoundError('Docker executable was not found. Install Docker Engine/Desktop with Compose, or use tools/windows/Start-Emulator.ps1 on Windows.') from exc
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError('Docker Compose timed out. Inspect docker compose logs; a container may still be running.') from exc


def up(config: dict[str, Any], adb: Adb) -> None:
    # The container owns its two cold-boot attempts. Wait for those attempts rather
    # than restarting it halfway through its own retry window.
    timeout = math.ceil(config['emulator']['boot_timeout_s']) * 2 + 90
    compose(config, 'up', '-d', '--wait', '--wait-timeout', str(timeout), 'emulator')
    wait_ready(adb, config['adb']['timeout_s'])
