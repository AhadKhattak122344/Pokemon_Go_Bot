"""Explicit debug-root management for owned Android emulators.

ADB daemon root and an app's Linux UID are distinct. This module does not install
Magisk, patch boot images, change verified-boot properties, or install modules.
"""
from __future__ import annotations

import math
import re
import subprocess
import time
from dataclasses import asdict, dataclass

from .adb import Adb


@dataclass(frozen=True)
class RootStatus:
    serial: str
    adb_uid: int
    adb_root: bool
    emulator: bool
    debuggable: bool
    build_type: str
    abi: str
    selinux: str | None
    magisk_binary: str | None
    modules: list[str] | None
    observations: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class RootManager:
    def __init__(self, adb: Adb):
        self.adb = adb

    def status(self) -> RootStatus:
        # Required probes fail rather than reporting a disconnected device as unrooted.
        uid = int(self.adb.shell('id', '-u', timeout=5))
        text = self.adb.shell('getprop', timeout=5)
        props = dict(re.findall(r'^\[([^\]]+)\]: \[(.*)\]$', text, re.MULTILINE))
        observations: list[str] = []

        def optional(label: str, *args: str) -> str | None:
            try:
                return self.adb.shell(*args, timeout=5) or None
            except subprocess.SubprocessError:
                observations.append(f'{label} unavailable to this ADB session')
                return None

        selinux = optional('SELinux status', 'getenforce')
        magisk = optional('Magisk executable', 'sh', '-c', 'command -v magisk')
        modules = None
        if uid == 0:
            listing = optional('Magisk module directory', 'ls', '-1', '/data/adb/modules')
            if listing is not None:
                modules = [line for line in listing.splitlines() if re.fullmatch(r'[A-Za-z0-9_.-]+', line)]
        else:
            observations.append('Module inventory requires an already-rooted ADB session')
        return RootStatus(self.adb.serial, uid, uid == 0,
                          props.get('ro.kernel.qemu') == '1' or props.get('ro.boot.qemu') == '1',
                          props.get('ro.debuggable') == '1', props.get('ro.build.type', 'unknown'),
                          props.get('ro.product.cpu.abilist', 'unknown'), selinux, magisk,
                          modules, observations)

    def set_enabled(self, enabled: bool, timeout_s: float = 45) -> dict:
        if not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError('Root transition timeout must be positive and finite')
        before = self.status()
        if not before.emulator:
            raise RuntimeError('Debug-root controls are restricted to emulator devices')
        if enabled and not before.debuggable:
            raise RuntimeError('This image is not debuggable; select an emulator image supporting adb root')
        wanted_uid = 0 if enabled else 2000
        if before.adb_uid == wanted_uid:
            return {'changed': False, 'before': before.to_dict(), 'after': before.to_dict()}

        deadline = time.monotonic() + timeout_s
        action = 'root' if enabled else 'unroot'
        response = str(self.adb.run(action, timeout=min(timeout_s, 10))).strip()
        if 'cannot' in response.lower() or 'failed' in response.lower():
            raise RuntimeError(f'ADB rejected {action}: {response}')
        last_error = 'ADB is reconnecting'
        while time.monotonic() < deadline:
            try:
                remaining = max(0.1, min(5, deadline - time.monotonic()))
                uid = int(self.adb.shell('id', '-u', timeout=remaining))
                if uid == wanted_uid:
                    after = self.status()
                    if after.adb_uid == wanted_uid:
                        return {'changed': True, 'response': response,
                                'before': before.to_dict(), 'after': after.to_dict()}
                last_error = f'Expected UID {wanted_uid}, observed UID {uid}'
            except (subprocess.SubprocessError, ValueError) as exc:
                last_error = str(exc)
            time.sleep(max(0, min(0.5, deadline - time.monotonic())))
        raise TimeoutError(f'{action} did not reach UID {wanted_uid}: {last_error}')

    def roundtrip(self) -> dict:
        """Exercise both modes, restoring the original ADB privilege in all cases."""
        original = self.status()
        if not original.emulator or not original.debuggable:
            raise RuntimeError('Root self-test needs a debuggable emulator')
        result: dict = {'original': original.to_dict()}
        try:
            result['root'] = self.set_enabled(True)
            result['non_root'] = self.set_enabled(False)
        finally:
            # Failure to restore is surfaced to the caller, never silently ignored.
            result['restored'] = self.set_enabled(original.adb_root)
        return result
