"""Bounded crash-classification experiments. No concealment or integrity bypass."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import diagnostics
from .adb import Adb
from .cli import resumed_activity
from .config import component, package_name, positive_number
from .health import wait_ready
from .root import RootManager


CONCEALMENT_MARKERS = (
    'playintegrityfix', 'play-integrity-fix', 'play_integrity_fix',
    'shamiko', 'safetynet-fix', 'safetynetfix', 'universal-safetynet',
    'zygisk-next', 'zygisk_next', 'lsposed', 'magiskhide',
    'device-emulator', 'deviceemulator', 'pif-',
)

SIGILL = re.compile(r'Fatal signal 4|SIGILL|Undefined instruction', re.I)
TRANSLATION = re.compile(r'ndk_translation|libhoudini|native.?bridge', re.I)
JAVA_CRASH = re.compile(r'FATAL EXCEPTION|AndroidRuntime:\s+FATAL', re.I)
ROOT_HINT = re.compile(r'SafetyNet|Play Integrity|CTS profile|root detected|MagiskHide', re.I)
SIGN_IN_FAIL = re.compile(r'Failed to Sign In|SIGN_IN_FAILED|SignInStatus.*ERROR|ApiException:\s*10|DEVELOPER_ERROR', re.I)
GOOGLE_SIGN_IN = re.compile(r'GOOGLE_SIGN_IN|AccountPickerActivity|SignInHubActivity|SignInActivity', re.I)
IN_GAME_HINT = re.compile(r'NearbyPok[eé]mon|MapScene|HoloholoMap|WorldScene', re.I)
ACCOUNT_PICKER = 'AccountPickerActivity'
SIGN_IN_ACTIVITY = ('SignInActivity', 'SignInHubActivity')


def assert_not_concealment_payload(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    haystack = resolved.name.lower().replace('_', '-')
    for marker in CONCEALMENT_MARKERS:
        if marker in haystack:
            raise ValueError(
                f'Refused concealment/integrity-bypass payload {resolved.name}. '
                'lab experiment captures crashes and launch evidence only.'
            )
    if resolved.suffix.lower() == '.zip':
        raise ValueError('ZIP Magisk modules are not installed by lab experiment')
    if 'magisk' in haystack:
        raise ValueError('Install Magisk with tools/windows/Install-Magisk.ps1, not lab experiment')
    if not resolved.is_file() or resolved.suffix.lower() != '.apk':
        raise ValueError('Pass an existing APK file')
    return resolved


def classify(package: str, installed: bool, launch_output: str, crash: str, logcat: str,
             resumed: bool, launched: bool = False) -> str:
    if not installed:
        return 'not_installed'
    text = '\n'.join((launch_output, crash, logcat))
    target_crash = crash if package in crash else ''
    if SIGILL.search(target_crash) and TRANSLATION.search(target_crash):
        return 'ndk_translation'
    if SIGILL.search(target_crash):
        return 'native_sigill'
    target_java_crash = re.search(
        r'(?:FATAL EXCEPTION|AndroidRuntime:\s+FATAL)[\s\S]{0,4096}Process:\s*'
        + re.escape(package)
        + r'|Process:\s*' + re.escape(package)
        + r'[\s\S]{0,4096}(?:FATAL EXCEPTION|AndroidRuntime:\s+FATAL)',
        crash, re.I,
    )
    if target_java_crash:
        return 'java_crash'
    if launched and 'Error:' in launch_output:
        return 'launch_error'
    if launched and any(package in line and ROOT_HINT.search(line) for line in text.splitlines()):
        return 'root_or_integrity_signal'
    if package in crash and re.search(r'Process:\s*' + re.escape(package), crash):
        return 'process_died'
    if resumed:
        return 'foreground_ok'
    return 'unknown'


def top_activity(adb: Adb) -> str:
    return adb.shell('dumpsys', 'activity', 'activities', timeout=8)


def ui_dump(adb: Adb) -> str:
    try:
        adb.shell('uiautomator', 'dump', '/sdcard/lab-uidump.xml', timeout=15)
        return adb.shell('cat', '/sdcard/lab-uidump.xml', timeout=10)
    except (TimeoutError, RuntimeError):
        return ''


def classify_login(activity: str, logcat: str, ui: str, package: str | None = None) -> str:
    top = next((line for line in activity.splitlines() if 'topResumedActivity' in line), '')
    if ACCOUNT_PICKER in top or 'Choose an account' in ui:
        return 'account_picker'
    if any(name in top for name in SIGN_IN_ACTIVITY):
        return 'google_signin'
    target_top = package is None or package in top
    target_logcat = logcat if package is None else '\n'.join(
        line for line in logcat.splitlines() if package in line
    )
    if (SIGN_IN_FAIL.search(target_logcat)
            or (target_top and ('Failed to Sign In' in ui or 'TRY A DIFFERENT ACCOUNT' in ui))):
        return 'sign_in_failed'
    if 'packageinstaller' in top.lower() or 'GRANT_RUNTIME_PERMISSIONS' in top:
        return 'post_login_permission'
    if IN_GAME_HINT.search(target_logcat):
        return 'in_game_signal'
    if GOOGLE_SIGN_IN.search(top):
        return 'google_oauth_seen'
    return 'splash_or_unknown'


def wait_login(adb: Adb, out: Path, timeout_s: float = 180,
               package: str | None = None) -> dict:
    """Observe Google/Niantic login without selecting an account."""
    positive_number(timeout_s, 'Login timeout')
    deadline = time.monotonic() + timeout_s
    stage = 'unknown'
    logcat = ''
    activity = ''
    transport_error = None
    while time.monotonic() < deadline:
        try:
            activity = top_activity(adb)
            ui = ui_dump(adb) if 'gms' in activity.lower() or ACCOUNT_PICKER in activity else ''
            logcat = str(adb.run('logcat', '-d', '-t', '80', timeout=15))
        except (TimeoutError, RuntimeError) as exc:
            stage = 'transport_error'
            transport_error = str(exc)
            break
        stage = classify_login(activity, logcat, ui, package)
        if stage == 'account_picker':
            stage = 'account_selection_required'
        if stage in ('account_selection_required', 'sign_in_failed', 'in_game_signal', 'post_login_permission'):
            break
        time.sleep(2)
    result = {'stage': stage, 'account_tapped': False, 'timeout_s': timeout_s}
    if transport_error is not None:
        result['error'] = transport_error
    try:
        (out / 'login.png').write_bytes(adb.screenshot())
    except (TimeoutError, RuntimeError) as exc:
        result['screenshot_error'] = str(exc)
    (out / 'login-logcat.txt').write_text(logcat, encoding='utf-8', errors='replace')
    (out / 'login-activity.txt').write_text(activity, encoding='utf-8', errors='replace')
    return result


def resolve_launcher(adb: Adb, package: str) -> str | None:
    output = adb.shell(
        'cmd', 'package', 'resolve-activity',
        '-a', 'android.intent.action.MAIN',
        '-c', 'android.intent.category.LAUNCHER',
        '--brief', package,
    )
    for line in reversed(output.splitlines()):
        line = line.strip()
        if '/' in line:
            try:
                return component(line, package)
            except ValueError:
                continue
    return None


def run(adb: Adb, cfg: dict, out: Path, *, package: str | None = None,
        launch: bool = False, apk: Path | None = None, login: bool = False,
        login_timeout_s: float = 180) -> dict:
    if login:
        positive_number(login_timeout_s, 'Login timeout')
    if apk is not None:
        apk = assert_not_concealment_payload(apk)
    out.mkdir(parents=True, exist_ok=False)
    target = package_name(package or cfg['app']['package'])
    report = {
        'serial': adb.serial, 'package': target, 'launch': launch,
        'apk': str(apk) if apk is not None else None, 'installed': False, 'launcher': None,
        'classification': 'unknown', 'resumed': False, 'login': login,
        'authentication': 'unverified', 'certification': 'not_tested',
        'concealment_modules': 'refused', 'start': time.time(), 'error': None,
    }
    try:
        wait_ready(adb, cfg['emulator']['boot_timeout_s'])
        if apk is not None:
            adb.run('install', '-r', str(apk), timeout=180)
        try:
            diagnostics.capture(adb, out / 'pre', target)
        except Exception as exc:
            report['capture_error'] = str(exc)
            raise
        installed = adb.shell('pm', 'path', target).startswith('package:')
        report['installed'] = installed
        try:
            report['root'] = RootManager(adb).status().to_dict()
        except (RuntimeError, TimeoutError, ValueError) as exc:
            report['root_error'] = str(exc)
        crash = (out / 'pre' / 'crash.txt').read_text(encoding='utf-8', errors='replace') if (out / 'pre' / 'crash.txt').is_file() else ''
        logcat = (out / 'pre' / 'logcat.txt').read_text(encoding='utf-8', errors='replace') if (out / 'pre' / 'logcat.txt').is_file() else ''
        launch_output = ''
        resumed = False
        if launch:
            if not installed:
                raise RuntimeError(f'App is not installed: {target}')
            launcher = resolve_launcher(adb, target) or cfg['app']['activity']
            component(launcher, target)
            report['launcher'] = launcher
            adb.run('logcat', '-b', 'all', '-c')
            # Do not use am start -W: Unity can fail to report launch and hang ADB.
            try:
                launch_output = adb.shell('am', 'start', '-S', '-n', launcher, timeout=60)
            except (TimeoutError, RuntimeError) as exc:
                launch_output = str(exc)
                report['launch_transport_error'] = str(exc)
            (out / 'launch.txt').write_text(launch_output, encoding='utf-8')
            deadline = time.monotonic() + 30
            expected = cfg['app'].get('ready_activity') or launcher
            while time.monotonic() < deadline:
                try:
                    activities = adb.shell('dumpsys', 'activity', 'activities', timeout=5)
                except (TimeoutError, RuntimeError):
                    break
                if resumed_activity(activities, expected):
                    resumed = True
                    break
                time.sleep(1)
            time.sleep(2)
            try:
                crash = str(adb.run('logcat', '-b', 'crash', '-d'))
                logcat = str(adb.run('logcat', '-b', 'all', '-d'))
            except (TimeoutError, RuntimeError) as exc:
                report['log_error'] = str(exc)
                crash, logcat = crash, logcat
            (out / 'crash.txt').write_text(crash, encoding='utf-8')
            (out / 'logcat.txt').write_text(logcat, encoding='utf-8')
            try:
                (out / 'launch.png').write_bytes(adb.screenshot())
            except (TimeoutError, RuntimeError) as exc:
                report['screenshot_error'] = str(exc)
            try:
                activities = top_activity(adb)
                (out / 'activity.txt').write_text(activities, encoding='utf-8', errors='replace')
                resumed = resumed_activity(activities, expected)
            except (TimeoutError, RuntimeError) as exc:
                report['activity_error'] = str(exc)
            report['resumed'] = resumed
            if login:
                login_report = wait_login(adb, out, login_timeout_s, target)
                report['login_result'] = login_report
                stage = login_report.get('stage')
                if stage == 'sign_in_failed':
                    report['authentication'] = 'niantic_sign_in_failed'
                elif stage in ('account_selection_required', 'google_signin', 'google_oauth_seen'):
                    report['authentication'] = 'google_oauth_incomplete_or_pending'
                try:
                    crash = str(adb.run('logcat', '-b', 'crash', '-d'))
                    logcat = str(adb.run('logcat', '-b', 'all', '-d'))
                    (out / 'crash.txt').write_text(crash, encoding='utf-8')
                    (out / 'logcat.txt').write_text(logcat, encoding='utf-8')
                except (TimeoutError, RuntimeError) as exc:
                    report['login_log_error'] = str(exc)
        report['classification'] = classify(
            target, installed, launch_output, crash, logcat, resumed, launched=launch,
        )
        if report.get('authentication') == 'niantic_sign_in_failed':
            report['classification'] = 'sign_in_failed'
        elif report.get('login_result', {}).get('stage') == 'in_game_signal':
            report['classification'] = 'in_game_signal'
    except Exception as exc:
        report['error'] = str(exc)
        if report['classification'] == 'unknown' and 'not installed' in str(exc).lower():
            report['classification'] = 'not_installed'
        raise
    finally:
        report['end'] = time.time()
        (out / 'experiment.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report
