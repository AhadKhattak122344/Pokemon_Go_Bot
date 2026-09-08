from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from . import config, emulator, location
from .adb import Adb
from .health import wait_ready
from .root import RootManager


def smoke(adb: Adb, cfg: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    started, error = time.time(), None
    try:
        wait_ready(adb, cfg['emulator']['boot_timeout_s'])
        package = cfg['app']['package']
        if not adb.shell('pm', 'path', package).startswith('package:'):
            raise RuntimeError('App is not installed; run lab install --apk <path> first')
        adb.run('logcat', '-c')
        result = adb.shell('am', 'start', '-W', '-n', cfg['app']['activity'])
        if 'Error:' in result or 'Status: ok' not in result:
            raise RuntimeError(f'Launch failed: {result}')
        deadline = time.monotonic() + 30
        expected = cfg['app'].get('ready_activity', cfg['app']['activity'])
        while time.monotonic() < deadline:
            activities = adb.shell('dumpsys', 'activity', 'activities')
            if any(expected in line and 'mResumedActivity' in line for line in activities.splitlines()):
                break
            time.sleep(1)
        else:
            raise RuntimeError(f'App never reached {expected}')
        time.sleep(2)
        crashes = str(adb.run('logcat', '-b', 'crash', '-d'))
        if f'Process: {package},' in crashes:
            raise RuntimeError('App crashed; see logcat.txt')
        (out / 'launch.png').write_bytes(adb.screenshot())
    except Exception as exc:
        error = str(exc)
    finally:
        collection_errors = []
        for filename, args in [('logcat.txt', ('logcat', '-d')),
                               ('dumpsys_location.txt', ('shell', 'dumpsys location'))]:
            try:
                (out / filename).write_text(str(adb.run(*args)), encoding='utf-8')
            except Exception as exc:
                collection_errors.append(f'{filename}: {exc}')
        (out / 'meta.json').write_text(json.dumps({'package': cfg['app']['package'],
            'api': cfg['emulator']['api'], 'start': started, 'end': time.time(),
            'error': error, 'collection_errors': collection_errors}, indent=2), encoding='utf-8')
        suite = ET.Element('testsuite', name='app-launch', tests='1', failures=str(int(error is not None)))
        case = ET.SubElement(suite, 'testcase', name='launch', time=str(time.time()-started))
        if error:
            ET.SubElement(case, 'failure', message=error).text = error
        ET.ElementTree(suite).write(out / 'junit.xml', encoding='utf-8', xml_declaration=True)
    if error:
        raise RuntimeError(error)


def main() -> None:
    parser = argparse.ArgumentParser(description='Build/test harness for the recovered Android app')
    parser.add_argument('--config', type=Path, default=Path('config/default.yaml'))
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('up', 'down', 'status', 'smoke'):
        commands.add_parser(name)
    root = commands.add_parser('root', help='Explicit emulator debug-root controls')
    root.add_argument('action', choices=['status', 'enable', 'disable', 'self-test'])
    root.add_argument('--out', type=Path, help='JSON report path; defaults to a unique artifacts file')
    install = commands.add_parser('install')
    install.add_argument('--apk', type=Path, required=True)
    loc = commands.add_parser('location').add_subparsers(dest='location_command', required=True)
    fix = loc.add_parser('set')
    fix.add_argument('--lat', type=float, required=True)
    fix.add_argument('--lon', type=float, required=True)
    route = loc.add_parser('follow')
    route.add_argument('--gpx', type=Path, required=True)
    route.add_argument('--speed-mps', type=float, default=1.4)
    args = parser.parse_args()
    try:
        cfg = config.load(args.config)
        adb = Adb(**cfg['adb'])
        if args.command == 'up':
            emulator.up(cfg, adb)
        elif args.command == 'down':
            emulator.compose(cfg, 'down', '--remove-orphans')
        elif args.command == 'status':
            print(adb.run('get-state'))
            print('boot_completed=' + adb.shell('getprop', 'sys.boot_completed'))
            print('ABI=' + adb.shell('getprop', 'ro.product.cpu.abilist'))
        elif args.command == 'root':
            out = args.out or Path(cfg['artifacts']) / ('root-' + uuid.uuid4().hex + '.json')
            out.parent.mkdir(parents=True, exist_ok=True)
            report = {'action': args.action, 'serial': adb.serial, 'start': time.time()}
            manager = RootManager(adb)
            try:
                if args.action == 'status':
                    report['result'] = manager.status().to_dict()
                elif args.action == 'self-test':
                    report['result'] = manager.roundtrip()
                else:
                    report['result'] = manager.set_enabled(args.action == 'enable')
            except Exception as exc:
                report['error'] = str(exc)
                raise
            finally:
                report['end'] = time.time()
                out.write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps(report, indent=2))
            print(f'Report: {out}')
        elif args.command == 'install':
            if not args.apk.is_file() or args.apk.suffix != '.apk':
                raise ValueError('Pass an existing APK file')
            print(adb.run('install', '-r', str(args.apk.resolve()), timeout=180))
        elif args.command == 'smoke':
            out = Path(cfg['artifacts']) / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
            smoke(adb, cfg, out)
            print(f'App launch passed. Artifacts: {out}')
        elif args.location_command == 'set':
            location.set_location(adb, location.Point(args.lat, args.lon))
        else:
            trace = Path(cfg['artifacts']) / (uuid.uuid4().hex + '-location_trace.csv')
            location.follow(adb, args.gpx, args.speed_mps, trace)
    except (OSError, ValueError, KeyError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'lab: {exc}\n')


if __name__ == '__main__':
    main()
