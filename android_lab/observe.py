"""Bounded, read-only Android app observation evidence capture.

An observation duration limits when a new sample may begin.  A sample is not
started during the final one-second window (or the configured ADB timeout when
that is shorter).  This guard avoids turning the natural end of an observation
into a tiny, artificial ADB timeout.  A sample that has started still receives
the normal bounded ADB timeout for each probe: a genuine device timeout remains
a collection failure and can be reported as such.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .adb import Adb
from .config import component, package_name, positive_number


_COMPONENT = re.compile(r'([A-Za-z][\w.]*)/(\.?[A-Za-z_$][\w.$]*)', re.ASCII)
_MIN_SAMPLE_START_WINDOW_S = 1.0


def foreground_activity(activities: str) -> str | None:
    """Return the resumed component reported by activity manager, if any."""
    for line in activities.splitlines():
        if not re.search(r'\b(?:mResumedActivity|topResumedActivity|ResumedActivity)\b', line):
            continue
        match = _COMPONENT.search(line)
        if match:
            package, activity = match.groups()
            return package + '/' + (package + activity if activity.startswith('.') else activity)
    return None


def _timeout(adb: Adb) -> float:
    """Keep each observation probe short even when the configured ADB limit is large."""
    configured = getattr(adb, 'timeout', 10)
    try:
        configured = float(configured)
    except (TypeError, ValueError):
        configured = 10
    return min(10.0, configured) if math.isfinite(configured) and configured > 0 else 10.0


def _sample_start_window(timeout_s: float) -> float:
    """Return the minimum remaining observation time needed to begin a sample."""
    return min(_MIN_SAMPLE_START_WINDOW_S, timeout_s)


def _pids(adb: Adb, package: str, timeout_s: float) -> list[int]:
    """Return target PIDs, treating pidof's normal no-match exit as evidence."""
    marker = '__LAB_PIDOF_STATUS:'
    output = adb.shell(
        'sh', '-c', f'pidof {package}; status=$?; printf "\\n{marker}%s\\n" "$status"',
        timeout=timeout_s,
    )
    status_match = re.search(marker + r'(\d+)', output)
    if status_match is None:
        raise RuntimeError('pidof did not return an exit status')
    status = int(status_match.group(1))
    if status == 1:
        return []
    if status != 0:
        raise RuntimeError(f'pidof failed with exit status {status}')
    return [int(pid) for pid in output[:status_match.start()].split() if pid.isdigit()]


def _screenshot(adb: Adb, timeout_s: float) -> bytes:
    """Capture a PNG with the same bounded timeout as the text probes."""
    data = adb.run('exec-out', 'screencap', '-p', timeout=timeout_s, binary=True)
    if not isinstance(data, bytes) or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('Device did not return a PNG screenshot')
    return data


def run(adb: Adb, cfg: dict[str, Any], out: Path, *, package: str | None = None,
        duration_s: float = 30, interval_s: float = 3, launch: bool = False,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        on_sample: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Capture periodic process/activity/screenshot evidence without app interaction.

    The only optional mutation is a configured-component launch after the first
    complete observation.  Any collection failure leaves the artifacts intact
    and makes the command fail after writing ``observe.json``.
    """
    positive_number(duration_s, 'Observation duration')
    positive_number(interval_s, 'Observation interval')
    configured_package = package_name(cfg['app']['package'])
    configured_component = component(cfg['app']['activity'], configured_package)
    target = package_name(package) if package else configured_package
    if launch and target is not None and target != configured_package:
        raise ValueError('--launch only supports the configured app package')

    out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    started_monotonic = clock()
    deadline = started_monotonic + float(duration_s)
    timeout_s = _timeout(adb)
    sample_start_window_s = _sample_start_window(timeout_s)
    evidence_path = out / 'evidence.jsonl'
    report: dict[str, Any] = {
        'serial': adb.serial,
        'package': target,
        'duration_s': duration_s,
        'interval_s': interval_s,
        'sample_start_window_s': sample_start_window_s,
        'launch_requested': launch,
        'launch_component': configured_component if launch else None,
        'launch_attempted': False,
        'launch_performed': False,
        'capture_complete': False,
        'capture_status': 'collecting',
        'app_running': 'not_observed',
        'samples': 0,
        'errors': [],
        'started': started,
    }
    observed_process = False
    sample_index = 0

    def sample() -> bool:
        nonlocal sample_index, observed_process
        sample_index += 1
        timestamp = time.time()
        item: dict[str, Any] = {'timestamp': timestamp, 'elapsed_s': clock() - started_monotonic,
                                'sample': sample_index, 'package': target, 'pids': [],
                                'foreground_activity': None, 'errors': []}
        complete = True
        device_available = True
        # The loop only starts a sample with a meaningful remaining observation
        # window.  Once started, retain the normal ADB timeout so an actual
        # device timeout is never relabelled as end-of-observation behavior.
        probe_timeout = timeout_s
        try:
            state = str(adb.run('get-state', timeout=probe_timeout)).strip()
            item['device_state'] = state
            if state != 'device':
                raise RuntimeError(f'ADB device is {state or "unavailable"}')
        except (OSError, RuntimeError, TimeoutError) as exc:
            item['errors'].append(f'device_state: {exc}')
            complete = False
            device_available = False
        if target is not None:
            try:
                item['pids'] = _pids(adb, target, probe_timeout)
                observed_process = observed_process or (device_available and bool(item['pids']))
            except (OSError, RuntimeError, TimeoutError) as exc:
                item['errors'].append(f'pidof: {exc}')
                complete = False
        activity_file = out / f'activity-{sample_index:04d}.txt'
        try:
            raw_activity = adb.shell('dumpsys', 'activity', 'activities', timeout=probe_timeout)
            activity_file.write_text(raw_activity, encoding='utf-8', errors='replace')
            item['activity_file'] = activity_file.name
            item['foreground_activity'] = foreground_activity(raw_activity)
        except (OSError, RuntimeError, TimeoutError) as exc:
            item['errors'].append(f'activity: {exc}')
            complete = False
        screen_file = out / f'screen-{sample_index:04d}.png'
        try:
            screen_file.write_bytes(_screenshot(adb, probe_timeout))
            item['screenshot_file'] = screen_file.name
        except (OSError, RuntimeError, TimeoutError) as exc:
            item['errors'].append(f'screenshot: {exc}')
            complete = False
        if item['errors']:
            report['errors'].extend(item['errors'])
        with evidence_path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(item, sort_keys=True) + '\n')
        report['samples'] = sample_index
        if on_sample is not None:
            on_sample(item)
        return complete

    try:
        initial_remaining_s = deadline - clock()
        if initial_remaining_s < sample_start_window_s:
            pre_capture_complete = False
            report['late_sample_skipped'] = True
            report['late_sample_remaining_s'] = max(0.0, initial_remaining_s)
        else:
            pre_capture_complete = sample()
        if launch:
            if not pre_capture_complete:
                report['launch_skipped'] = 'pre-capture incomplete'
            else:
                try:
                    # The configured component is the only component this command may start.
                    report['launch_attempted'] = True
                    result = adb.shell('am', 'start', '-n', configured_component, timeout=timeout_s)
                    if 'error:' in result.lower():
                        raise RuntimeError(f'Configured component launch failed: {result}')
                    report['launch_performed'] = True
                    with evidence_path.open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps({'timestamp': time.time(), 'event': 'launch',
                                                 'component': configured_component, 'result': result}) + '\n')
                except (OSError, RuntimeError, TimeoutError) as exc:
                    report['errors'].append(f'launch: {exc}')
        while clock() < deadline:
            sleep(min(float(interval_s), max(0.0, deadline - clock())))
            remaining_s = deadline - clock()
            if remaining_s < sample_start_window_s:
                if remaining_s > 0:
                    report['late_sample_skipped'] = True
                    report['late_sample_remaining_s'] = remaining_s
                break
            sample()
        report['capture_complete'] = report['samples'] > 0 and not report['errors']
        report['capture_status'] = 'captured' if report['capture_complete'] else 'partial'
        report['app_running'] = 'observed' if observed_process else 'not_observed'
    finally:
        report['ended'] = time.time()
        (out / 'observe.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if not report['capture_complete']:
        raise RuntimeError(f"Observation capture incomplete; inspect {out / 'observe.json'}")
    return report
