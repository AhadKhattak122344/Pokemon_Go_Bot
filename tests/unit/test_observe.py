import json
import math
from unittest.mock import Mock

import pytest

from android_lab.adb import Adb
from android_lab.observe import run


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class AdvancingClock(Clock):
    """A monotonic clock whose ADB operations consume realistic elapsed time."""

    def advance(self, seconds):
        self.value += seconds


def configured_adb(*, pid='42', activity='topResumedActivity=ActivityRecord{ com.example.app/.MainActivity }'):
    adb = Mock(spec=Adb, serial='emulator-5556')
    adb.timeout = 5
    def adb_run(*args, **kwargs):
        if args[:3] == ('exec-out', 'screencap', '-p'):
            return b'\x89PNG\r\n\x1a\n'
        return 'device'

    adb.run.side_effect = adb_run

    def shell(*args, **kwargs):
        if args[:2] == ('sh', '-c'):
            return (pid + '\n' if pid else '') + '__LAB_PIDOF_STATUS:' + ('0' if pid else '1')
        if args[:3] == ('dumpsys', 'activity', 'activities'):
            return activity
        return ''

    adb.shell.side_effect = shell
    return adb


def config():
    return {'app': {'package': 'com.example.app', 'activity': 'com.example.app/.MainActivity'}}


def test_observe_records_absent_pid_without_calling_it_a_capture_failure(tmp_path):
    clock = Clock()
    report = run(configured_adb(pid=''), config(), tmp_path / 'out', package='com.example.app',
                 duration_s=2, interval_s=1, clock=clock, sleep=clock.sleep)
    evidence = [json.loads(line) for line in (tmp_path / 'out' / 'evidence.jsonl').read_text().splitlines()]
    assert report['capture_complete'] is True
    assert report['app_running'] == 'not_observed'
    assert evidence[0]['pids'] == []
    assert (tmp_path / 'out' / 'activity-0001.txt').is_file()
    assert (tmp_path / 'out' / 'screen-0001.png').is_file()


def test_observe_keeps_unrelated_foreground_separate_from_target_process(tmp_path):
    clock = Clock()
    report = run(configured_adb(activity='topResumedActivity=ActivityRecord{ com.other/.OtherActivity }'),
                 config(), tmp_path / 'out', package='com.example.app', duration_s=1, interval_s=1,
                 clock=clock, sleep=clock.sleep)
    evidence = json.loads((tmp_path / 'out' / 'evidence.jsonl').read_text().splitlines()[0])
    assert report['app_running'] == 'observed'
    assert evidence['foreground_activity'] == 'com.other/com.other.OtherActivity'
    assert evidence['foreground_activity'] != 'com.example.app/com.example.app.MainActivity'


def test_observe_skips_a_late_sample_without_creating_an_artificial_timeout(tmp_path):
    clock = AdvancingClock()
    adb = configured_adb()
    adb_run = adb.run.side_effect
    adb_shell = adb.shell.side_effect

    def timed_run(*args, **kwargs):
        clock.advance(0.16)
        return adb_run(*args, **kwargs)

    def timed_shell(*args, **kwargs):
        clock.advance(0.16)
        return adb_shell(*args, **kwargs)

    adb.run.side_effect = timed_run
    adb.shell.side_effect = timed_shell
    report = run(adb, config(), tmp_path / 'out', package='com.example.app',
                 duration_s=8, interval_s=2, clock=clock, sleep=clock.sleep)

    evidence = [json.loads(line) for line in (tmp_path / 'out' / 'evidence.jsonl').read_text().splitlines()]
    assert report['capture_complete'] is True
    assert report['samples'] == 3
    assert report['late_sample_skipped'] is True
    assert 0 < report['late_sample_remaining_s'] < report['sample_start_window_s']
    assert all(not item['errors'] for item in evidence)
    assert all(call.kwargs['timeout'] == 5 for call in adb.run.call_args_list)


def test_observe_keeps_a_real_device_timeout_as_a_failure(tmp_path):
    clock = Clock()
    adb = configured_adb()

    def timed_out_run(*args, **kwargs):
        if args[:3] == ('exec-out', 'screencap', '-p'):
            raise TimeoutError('screencap timed out')
        return 'device'

    adb.run.side_effect = timed_out_run
    with pytest.raises(RuntimeError, match='Observation capture incomplete'):
        run(adb, config(), tmp_path / 'out', package='com.example.app', duration_s=2,
            interval_s=2, clock=clock, sleep=clock.sleep)
    report = json.loads((tmp_path / 'out' / 'observe.json').read_text())
    assert 'screenshot: screencap timed out' in report['errors']


def test_observe_does_not_start_an_initial_sample_without_the_start_window(tmp_path):
    clock = Clock()
    adb = configured_adb()
    with pytest.raises(RuntimeError, match='Observation capture incomplete'):
        run(adb, config(), tmp_path / 'out', package='com.example.app', duration_s=0.5,
            interval_s=1, clock=clock, sleep=clock.sleep)
    report = json.loads((tmp_path / 'out' / 'observe.json').read_text())
    assert report['samples'] == 0
    assert report['late_sample_skipped'] is True
    assert adb.mock_calls == []


def test_disconnect_preserves_partial_report_and_fails(tmp_path):
    clock = Clock()
    adb = configured_adb()
    def offline_run(*args, **kwargs):
        if args[:3] == ('exec-out', 'screencap', '-p'):
            return b'\x89PNG\r\n\x1a\n'
        return 'offline'
    adb.run.side_effect = offline_run
    with pytest.raises(RuntimeError, match='Observation capture incomplete'):
        run(adb, config(), tmp_path / 'out', package='com.example.app', duration_s=1,
            interval_s=1, clock=clock, sleep=clock.sleep)
    report = json.loads((tmp_path / 'out' / 'observe.json').read_text())
    evidence = json.loads((tmp_path / 'out' / 'evidence.jsonl').read_text().splitlines()[0])
    assert report['capture_complete'] is False
    assert report['capture_status'] == 'partial'
    assert report['app_running'] == 'not_observed'
    assert evidence['errors'][0].startswith('device_state:')


@pytest.mark.parametrize('duration, interval', [(0, 1), (1, 0), (-1, 1), (1, math.inf), (math.nan, 1)])
def test_invalid_observation_parameters_do_not_touch_device_or_output(tmp_path, duration, interval):
    adb = configured_adb()
    with pytest.raises(ValueError, match='positive finite'):
        run(adb, config(), tmp_path / 'out', duration_s=duration, interval_s=interval)
    assert adb.mock_calls == []
    assert not (tmp_path / 'out').exists()


def test_launch_is_skipped_when_pre_capture_is_incomplete(tmp_path):
    clock = Clock()
    adb = configured_adb()
    def no_screen(*args, **kwargs):
        if args[:3] == ('exec-out', 'screencap', '-p'):
            raise RuntimeError('screen unavailable')
        return 'device'
    adb.run.side_effect = no_screen
    with pytest.raises(RuntimeError):
        run(adb, config(), tmp_path / 'out', launch=True, duration_s=1, interval_s=1,
            clock=clock, sleep=clock.sleep)
    report = json.loads((tmp_path / 'out' / 'observe.json').read_text())
    assert report['launch_performed'] is False
    assert report['launch_skipped'] == 'pre-capture incomplete'
    assert not any(call.args[:2] == ('am', 'start') for call in adb.shell.call_args_list)


def test_pidof_transport_failure_is_not_treated_as_an_absent_process(tmp_path):
    clock = Clock()
    adb = configured_adb()
    def shell(*args, **kwargs):
        if args[:2] == ('sh', '-c'):
            return '__LAB_PIDOF_STATUS:127'
        if args[:3] == ('dumpsys', 'activity', 'activities'):
            return 'topResumedActivity=ActivityRecord{ com.example.app/.MainActivity }'
        return ''
    adb.shell.side_effect = shell
    with pytest.raises(RuntimeError, match='Observation capture incomplete'):
        run(adb, config(), tmp_path / 'out', package='com.example.app', duration_s=1,
            interval_s=1, clock=clock, sleep=clock.sleep)
    assert 'pidof failed with exit status 127' in json.loads((tmp_path / 'out' / 'observe.json').read_text())['errors'][0]


def test_launch_error_output_is_a_failure_and_samples_are_published(tmp_path):
    clock = Clock()
    adb = configured_adb()
    published = []
    original_shell = adb.shell.side_effect
    def shell(*args, **kwargs):
        if args[:2] == ('am', 'start'):
            return 'Error: Activity class does not exist.'
        return original_shell(*args, **kwargs)
    adb.shell.side_effect = shell
    with pytest.raises(RuntimeError, match='Observation capture incomplete'):
        run(adb, config(), tmp_path / 'out', launch=True, duration_s=1, interval_s=1,
            clock=clock, sleep=clock.sleep, on_sample=published.append)
    report = json.loads((tmp_path / 'out' / 'observe.json').read_text())
    assert report['launch_attempted'] is True
    assert report['launch_performed'] is False
    assert published and published[0]['sample'] == 1
