import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from orchestrator import config, emulator
from orchestrator.adb import Adb
from orchestrator.cli import main, resumed_activity, smoke
from orchestrator.health import wait_ready


@pytest.fixture
def cfg():
    return config.load(Path(__file__).resolve().parents[2] / 'config/default.yaml')


def test_null_ready_activity_successfully_launches_and_writes_artifacts(cfg, tmp_path):
    adb = Mock(serial='emulator-5554')
    def shell(*args, **kwargs):
        if args[:2] == ('pm', 'path'):
            return 'package:/data/app/base.apk'
        if args[:2] == ('am', 'start'):
            return 'Status: ok'
        if args == ('dumpsys', 'activity', 'activities'):
            # Android can expand the class name even when config uses shorthand.
            return 'topResumedActivity=ActivityRecord{123 u0 com.example.app/com.example.app.MainActivity t1}'
        raise AssertionError(args)
    adb.shell.side_effect = shell
    adb.run.return_value = ''
    adb.screenshot.return_value = b'\x89PNG\r\n\x1a\n'
    with patch('orchestrator.cli.wait_ready'), patch('orchestrator.cli.time.sleep'):
        smoke(adb, cfg, tmp_path)
    assert json.loads((tmp_path / 'meta.json').read_text())['error'] is None
    assert 'failures="0"' in (tmp_path / 'junit.xml').read_text()
    assert (tmp_path / 'launch.png').read_bytes().startswith(b'\x89PNG')
    adb.shell.assert_any_call('am', 'start', '-S', '-W', '-n', cfg['app']['activity'])


@pytest.mark.parametrize('line, expected', [
    ('mResumedActivity: com.example.app/.MainActivity', True),
    ('topResumedActivity=com.example.app/com.example.app.MainActivity', True),
    ('mResumedActivity: com.example.app/.MainActivityBackup', False),
    ('mResumedActivity: com.example.application/.MainActivity', False),
    ('lastResumedActivity: com.example.app/.MainActivity', False),
    ('mResumedActivity: com.other.app/.MainActivity', False),
])
def test_activity_matching_is_exact_and_supports_android_variants(line, expected):
    assert resumed_activity(line, 'com.example.app/.MainActivity') is expected


@pytest.mark.parametrize('failure', ['subprocess_crash', 'artifact', 'lost_foreground'])
def test_smoke_rejects_crash_missing_artifacts_or_activity_exit(cfg, tmp_path, failure):
    adb = Mock()
    foreground_checks = 0
    def shell(*args, **kwargs):
        nonlocal foreground_checks
        if args[:2] == ('pm', 'path'):
            return 'package:/data/app/base.apk'
        if args[:2] == ('am', 'start'):
            return 'Status: ok'
        foreground_checks += 1
        return '' if failure == 'lost_foreground' and foreground_checks > 1 else 'mResumedActivity: com.example.app/.MainActivity'
    def run(*args, **kwargs):
        if args == ('logcat', '-b', 'crash', '-d') and failure == 'subprocess_crash':
            return 'Process: com.example.app:worker, PID: 12'
        if args == ('logcat', '-b', 'all', '-d') and failure == 'artifact':
            raise subprocess.CalledProcessError(1, args)
        return ''
    adb.shell.side_effect = shell
    adb.run.side_effect = run
    adb.screenshot.return_value = b'\x89PNG\r\n\x1a\n'
    with patch('orchestrator.cli.wait_ready'), patch('orchestrator.cli.time.sleep'):
        with pytest.raises(RuntimeError):
            smoke(adb, cfg, tmp_path)
    assert json.loads((tmp_path / 'meta.json').read_text())['error']
    assert 'failures="1"' in (tmp_path / 'junit.xml').read_text()


def test_boot_waits_for_package_manager_and_recovers_from_offline():
    adb = Mock()
    adb.run.side_effect = [subprocess.CalledProcessError(1, []), 'device', 'device']
    adb.shell.side_effect = ['1', 'Error: Could not access the Package Manager', '1', 'package:/system/framework/framework-res.apk']
    with patch('orchestrator.health.time.sleep'):
        wait_ready(adb, 5)
    assert adb.run.call_count == 3
    assert adb.shell.call_count == 4


def test_boot_timeout_reports_not_ready_package_manager():
    adb = Mock()
    adb.run.return_value = 'device'
    adb.shell.side_effect = ['1', '']
    with patch('orchestrator.health.time.monotonic', side_effect=[0, 0, 0, 0, 0, 1, 1]), \
         patch('orchestrator.health.time.sleep'):
        with pytest.raises(TimeoutError, match='package manager'):
            wait_ready(adb, 1)


@pytest.mark.parametrize('invalid', [0, -1, float('nan'), float('inf'), True, '30'])
def test_invalid_timeouts_are_rejected_without_running_adb(invalid):
    with pytest.raises(ValueError):
        Adb(timeout_s=invalid)
    adb = Adb()
    with patch('subprocess.run') as run:
        with pytest.raises(ValueError):
            adb.run('get-state', timeout=invalid)
        run.assert_not_called()
    with pytest.raises(ValueError):
        wait_ready(adb, invalid)


@pytest.mark.parametrize('section, key, value', [
    ('app', 'package', None), ('app', 'activity', 3),
    ('app', 'ready_activity', []), ('app', 'permissions', ['android.permission.CAMERA']),
    ('adb', 'timeout_s', False), ('adb', 'serial', ''),
    ('emulator', 'boot_timeout_s', float('nan')), ('emulator', 'api', True),
    ('profiles', 'cheap-cloud', {'accel': True, 'gpu': 'auto'}),
])
def test_malformed_configuration_has_actionable_error(cfg, tmp_path, section, key, value):
    cfg[section][key] = value
    path = tmp_path / 'bad.yaml'
    path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError):
        config.load(path)


def test_missing_section_and_invalid_yaml_are_configuration_errors(tmp_path):
    path = tmp_path / 'bad.yaml'
    for content in ('app: []', 'app: ['):
        path.write_text(content)
        with pytest.raises(ValueError):
            config.load(path)


def test_environment_overrides_are_validated(cfg, tmp_path, monkeypatch):
    path = tmp_path / 'config.yaml'
    path.write_text(yaml.safe_dump(cfg))
    monkeypatch.setenv('LAB_SERIAL', '')
    with pytest.raises(ValueError, match='serial'):
        config.load(path)


def test_default_config_is_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert config.load(config.default_path())['emulator']['api'] == 34
    packaged = Path(config.__file__).with_name('default.yaml')
    assert yaml.safe_load(packaged.read_text()) == yaml.safe_load(config.default_path().read_text())


def test_compose_uses_acceleration_and_timeout_from_selected_profile(cfg):
    cfg['profile'] = 'custom'
    cfg['profiles']['custom'] = {'accel': 'on', 'gpu': 'host'}
    cfg['emulator']['boot_timeout_s'] = 42.5
    with patch('orchestrator.emulator.subprocess.run') as run:
        emulator.compose(cfg, 'up', '-d', 'emulator')
    command = run.call_args.args[0]
    env = run.call_args.kwargs['env']
    assert any(value.endswith('docker-compose.kvm.yml') for value in command)
    assert env['EMULATOR_ACCEL'] == 'on'
    assert env['EMULATOR_GPU'] == 'host'
    assert env['BOOT_TIMEOUT'] == '43'
    assert env['BOOT_HEALTH_START_PERIOD'] == '146s'


def test_compose_rejects_configuration_the_image_cannot_honor(cfg):
    cfg['emulator']['api'] = 35
    with patch('orchestrator.emulator.subprocess.run') as run:
        with pytest.raises(ValueError, match='34'):
            emulator.compose(cfg, 'up')
        run.assert_not_called()


def test_startup_waits_for_container_owned_retry_window(cfg):
    adb = Mock()
    with patch('orchestrator.emulator.compose') as compose, patch('orchestrator.emulator.wait_ready') as wait:
        emulator.up(cfg, adb)
    compose.assert_called_once_with(cfg, 'up', '-d', '--wait', '--wait-timeout', '1290', 'emulator')
    wait.assert_called_once_with(adb, 30)


def test_status_exits_nonzero_for_booting_device(cfg):
    with patch('sys.argv', ['lab', 'status']), patch('orchestrator.cli.config.load', return_value=cfg), \
         patch('orchestrator.cli.wait_ready', side_effect=TimeoutError('still booting')):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 1
