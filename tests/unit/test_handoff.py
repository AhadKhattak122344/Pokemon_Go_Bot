import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from android_lab.adb import Adb
from android_lab.cli import main
from android_lab.diagnostics import capture
from android_lab.health import wait_ready
from android_lab import config, emulator
from android_lab.root import RootManager


def test_diagnostics_collects_without_clearing_logs_or_changing_root(tmp_path):
    adb = Mock(serial='emulator-5556')
    adb.run.return_value = 'device'
    adb.screenshot.return_value = b'\x89PNG\r\n\x1a\n'
    out = tmp_path / 'capture'
    result = capture(adb, out, 'com.example.app')
    assert result['status'] == 'captured'
    assert result['authentication'] == 'unverified'
    assert (out / 'crash.txt').is_file()
    assert (out / 'target-package.txt').is_file()
    assert all('-c' not in c.args and 'root' not in c.args and 'install' not in c.args for c in adb.run.call_args_list)


def test_failed_capture_keeps_partial_evidence_and_failure_report(tmp_path):
    adb = Mock(serial='emulator-5556')
    adb.run.side_effect = RuntimeError('offline')
    adb.screenshot.side_effect = RuntimeError('offline')
    out = tmp_path / 'partial'
    with pytest.raises(RuntimeError, match='incomplete'):
        capture(adb, out)
    report = json.loads((out / 'report.json').read_text())
    assert report['status'] == 'partial'
    assert 'crash.txt' in report['errors']


def test_capture_preserves_existing_directory_and_rejects_shell_injection(tmp_path):
    adb = Mock()
    with pytest.raises(FileExistsError):
        capture(adb, tmp_path)
    with pytest.raises(ValueError):
        capture(adb, tmp_path / 'new', 'app; reboot')
    adb.run.assert_not_called()


@pytest.mark.parametrize('error, expected, message', [
    (FileNotFoundError(), FileNotFoundError, 'platform-tools'),
    (subprocess.TimeoutExpired('adb', 1), TimeoutError, 'timed out'),
    (subprocess.CalledProcessError(1, 'adb', stderr='device unauthorized'), RuntimeError, 'unauthorized'),
])
def test_adb_errors_are_actionable(error, expected, message):
    with patch('android_lab.adb.subprocess.run', side_effect=error):
        with pytest.raises(expected, match=message):
            Adb().run('get-state')


def test_missing_adb_fails_boot_wait_immediately():
    adb = Mock()
    adb.run.side_effect = FileNotFoundError('Install platform-tools')
    with pytest.raises(FileNotFoundError):
        wait_ready(adb, 600)
    assert adb.run.call_count == 1


def test_tcp_connect_verifies_authorization_and_reported_failure():
    adb = Adb(serial='192.0.2.10:5555')
    with patch.object(adb, 'run', side_effect=['connected', 'device']):
        assert adb.connect() == 'connected'
    with patch.object(adb, 'run', return_value='failed to connect'):
        with pytest.raises(RuntimeError, match='connection failed'):
            adb.connect()
    with patch.object(adb, 'run', side_effect=['connected', 'unauthorized']):
        with pytest.raises(RuntimeError, match='authorized'):
            adb.connect()


@pytest.mark.parametrize('serial', ['emulator-5556', 'a;reboot:5555', 'host:99999'])
def test_connect_rejects_bad_endpoint(serial):
    with pytest.raises(ValueError):
        Adb(serial=serial).connect()


def test_docker_missing_has_actionable_message():
    cfg = config.load(config.default_path())
    with patch('android_lab.emulator.subprocess.run', side_effect=FileNotFoundError()):
        with pytest.raises(FileNotFoundError, match='Docker executable was not found'):
            emulator.compose(cfg, 'down')


def test_new_commands_are_exposed_in_installed_cli(capsys):
    with patch('sys.argv', ['lab', '--help']), pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 0
    help_text = capsys.readouterr().out
    assert all(name in help_text for name in ('proxmox', 'diagnostics', 'connect', 'experiment'))


def test_proxmox_cli_dispatches_without_android_config():
    with patch('sys.argv', ['lab', 'proxmox', 'plan', '--config', 'fleet.json']), \
         patch('android_lab.cli.proxmox.main', return_value=0) as call, \
         patch('android_lab.cli.config.load') as load, pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 0
    call.assert_called_once_with(['plan', '--config', 'fleet.json'])
    load.assert_not_called()


def test_root_optional_probe_records_wrapped_adb_failure():
    adb = Mock(serial='emulator-5554')
    adb.shell.side_effect = ['2000', '[ro.kernel.qemu]: [1]', RuntimeError('unavailable'), RuntimeError('missing')]
    result = RootManager(adb).status()
    assert result.magisk_binary is None
    assert len(result.observations) == 3
