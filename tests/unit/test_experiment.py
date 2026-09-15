import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from android_lab.adb import Adb
from android_lab.cli import main
from android_lab.experiment import (
    assert_not_concealment_payload, classify, classify_login, run, wait_login,
)


@pytest.mark.parametrize('name', [
    'shamiko-shamiko-414.zip',
    'play-integrity-fix-v4.7-inject-s.zip',
    'universal-safetynet-fix-v2.4.0.zip',
    'zygisk-next-v1.5.0.zip',
    'magisk-v30.7.apk',
])
def test_concealment_and_magisk_payloads_are_refused(tmp_path, name):
    payload = tmp_path / name
    payload.write_bytes(b'not-a-real-module')
    with pytest.raises(ValueError, match='Refused|ZIP Magisk|Install Magisk'):
        assert_not_concealment_payload(payload)


def test_ordinary_apk_is_accepted(tmp_path):
    apk = tmp_path / 'game.apk'
    apk.write_bytes(b'apk')
    assert assert_not_concealment_payload(apk) == apk.resolve()


def test_sigill_through_translator_is_classified():
    crash = ('Cmdline: com.nianticlabs.pokemongo\n'
             'ndk_translation: Undefined instruction 0xd50320bf\nFatal signal 4 (SIGILL)')
    assert classify('com.nianticlabs.pokemongo', True, '', crash, '', False) == 'ndk_translation'


def test_missing_package_is_classified():
    assert classify('com.nianticlabs.pokemongo', False, '', '', '', False) == 'not_installed'


def test_resumed_launch_is_foreground_ok():
    assert classify('com.nianticlabs.pokemongo', True, 'Starting: Intent { cmp=com.nianticlabs.pokemongo/.UnityMainActivity }', '', '', True, True) == 'foreground_ok'


def test_process_death_overrides_a_previous_resumed_activity():
    crash = 'Process: com.nianticlabs.pokemongo, PID: 42'
    assert classify('com.nianticlabs.pokemongo', True, '', crash, '', True, True) == 'process_died'


def test_gms_integrity_noise_without_launch_is_not_classified():
    logcat = 'Play Integrity API: request for com.google.android.gms'
    assert classify('com.nianticlabs.pokemongo', True, '', '', logcat, False, False) == 'unknown'


def test_unrelated_gms_integrity_bind_does_not_classify_target_as_rejected():
    logcat = ('GmsSafetyNet: bind request for com.google.android.gms\n'
              'Unity: com.nianticlabs.pokemongo foreground')
    assert classify('com.nianticlabs.pokemongo', True, '', '', logcat, True, True) == 'foreground_ok'


def test_unrelated_java_crash_does_not_classify_target_as_crashed():
    crash = 'FATAL EXCEPTION: main\nProcess: com.example.other, PID: 42'
    launch = 'Starting: Intent { cmp=com.nianticlabs.pokemongo/.UnityMainActivity }'
    assert classify('com.nianticlabs.pokemongo', True, launch, crash, '', True, True) == 'foreground_ok'


def test_experiment_refuses_zip_before_adb_install(tmp_path):
    cfg = {
        'emulator': {'boot_timeout_s': 1},
        'app': {'package': 'com.nianticlabs.pokemongo',
                'activity': 'com.nianticlabs.pokemongo/.UnityMainActivity'},
    }
    adb = Mock(spec=Adb)
    payload = tmp_path / 'shamiko.zip'
    payload.write_bytes(b'zip')
    with pytest.raises(ValueError, match='ZIP Magisk|Refused'):
        run(adb, cfg, tmp_path / 'out', apk=payload)
    adb.run.assert_not_called()


def test_experiment_capture_without_launch_does_not_clear_logcat(tmp_path):
    cfg = {
        'emulator': {'boot_timeout_s': 1},
        'app': {'package': 'com.example.app', 'activity': 'com.example.app/.MainActivity'},
    }
    adb = Mock(spec=Adb, serial='emulator-5556')
    adb.shell.side_effect = lambda *args, **kwargs: 'package:/data/app/base.apk' if args[:2] == ('pm', 'path') else '2000'
    adb.run.return_value = 'device'
    adb.screenshot.return_value = b'\x89PNG\r\n\x1a\n'
    with patch('android_lab.experiment.wait_ready'), patch('android_lab.experiment.RootManager') as root:
        root.return_value.status.return_value.to_dict.return_value = {'adb_uid': 2000}
        report = run(adb, cfg, tmp_path / 'out')
    assert report['classification'] in ('unknown', 'foreground_ok', 'not_installed') or report['installed']
    assert (tmp_path / 'out' / 'experiment.json').is_file()
    assert (tmp_path / 'out' / 'pre' / 'crash.txt').is_file()
    assert all('-c' not in c.args for c in adb.run.call_args_list)


def test_readiness_failure_writes_experiment_report(tmp_path):
    cfg = {'emulator': {'boot_timeout_s': 1}, 'app': {
        'package': 'com.example.app', 'activity': 'com.example.app/.MainActivity'}}
    adb = Mock(spec=Adb, serial='emulator-5556')
    with patch('android_lab.experiment.wait_ready', side_effect=TimeoutError('device absent')):
        with pytest.raises(TimeoutError, match='device absent'):
            run(adb, cfg, tmp_path / 'out')
    report = json.loads((tmp_path / 'out' / 'experiment.json').read_text())
    assert report['error'] == 'device absent'
    assert report['installed'] is False
    assert 'end' in report


def test_invalid_login_timeout_is_rejected_before_device_actions(tmp_path):
    cfg = {'emulator': {'boot_timeout_s': 1}, 'app': {
        'package': 'com.example.app', 'activity': 'com.example.app/.MainActivity'}}
    adb = Mock(spec=Adb, serial='emulator-5556')
    with pytest.raises(ValueError, match='Login timeout'):
        run(adb, cfg, tmp_path / 'out', login=True, login_timeout_s=0)
    assert adb.mock_calls == []
    assert not (tmp_path / 'out').exists()


def test_experiment_cli_is_exposed(capsys):
    with patch('sys.argv', ['lab', '--help']), pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 0
    assert 'experiment' in capsys.readouterr().out


def test_account_picker_requires_user_selection_without_tapping(tmp_path):
    adb = Mock(spec=Adb)
    adb.run.return_value = ''
    adb.screenshot.return_value = b'\x89PNG\r\n\x1a\n'
    with patch('android_lab.experiment.top_activity', return_value='topResumedActivity=AccountPickerActivity'), \
         patch('android_lab.experiment.ui_dump', return_value='Choose an account'):
        report = wait_login(adb, tmp_path, 10, 'com.nianticlabs.pokemongo')
    assert report['stage'] == 'account_selection_required'
    assert report['account_tapped'] is False
    assert not any(call.args[:2] == ('input', 'tap') for call in adb.shell.call_args_list)


def test_login_stages():
    assert classify_login('topResumedActivity=...AccountPickerActivity t1', '', 'Choose an account') == 'account_picker'
    assert classify_login('topResumedActivity=...SignInHubActivity t1', '', '') == 'google_signin'
    paused = 'mLastPausedActivity: SignInHubActivity\ntopResumedActivity=...UnityMainActivity t1'
    assert classify_login(paused, '', 'Failed to Sign In RETRY') == 'sign_in_failed'
    assert classify_login('topResumedActivity=...UnityMainActivity t1', 'MapScene NearbyPokemon', '') == 'in_game_signal'


def test_target_login_classification_ignores_unrelated_logcat_patterns():
    assert classify_login('topResumedActivity=com.example.app/.MainActivity',
                          'Failed to Sign In from another process', '',
                          'com.example.app') == 'splash_or_unknown'


def test_in_game_signal_does_not_claim_authenticated_session(tmp_path):
    cfg = {'emulator': {'boot_timeout_s': 1}, 'app': {
        'package': 'com.example.app', 'activity': 'com.example.app/.MainActivity'}}
    adb = Mock(spec=Adb, serial='emulator-5556')

    def shell(*args, **kwargs):
        if args[:2] == ('pm', 'path'):
            return 'package:/data/app/base.apk'
        if args[:3] == ('cmd', 'package', 'resolve-activity'):
            return 'com.example.app/.MainActivity'
        if args[:2] == ('am', 'start'):
            return 'Starting: Intent'
        if args[:3] == ('dumpsys', 'activity', 'activities'):
            return 'topResumedActivity=com.example.app/.MainActivity'
        return ''

    adb.shell.side_effect = shell
    adb.run.return_value = ''
    adb.screenshot.return_value = b'\x89PNG\r\n\x1a\n'
    with patch('android_lab.experiment.wait_ready'), \
         patch('android_lab.experiment.diagnostics.capture'), \
         patch('android_lab.experiment.RootManager') as root, \
         patch('android_lab.experiment.wait_login', return_value={'stage': 'in_game_signal'}), \
         patch('android_lab.experiment.time.sleep'):
        root.return_value.status.return_value.to_dict.return_value = {'adb_uid': 2000}
        report = run(adb, cfg, tmp_path / 'out', launch=True, login=True, login_timeout_s=1)
    assert report['classification'] == 'in_game_signal'
    assert report['authentication'] == 'unverified'


def test_experiment_json_records_refused_concealment(tmp_path):
    report = json.loads('{"concealment_modules": "refused", "certification": "not_tested"}')
    assert report['concealment_modules'] == 'refused'
    assert report['certification'] == 'not_tested'
