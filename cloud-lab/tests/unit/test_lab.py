import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from orchestrator.adb import Adb
from orchestrator.config import component, load
from orchestrator.location import Point, distance, follow, read_gpx, updates
from orchestrator.cli import smoke


def test_adb_keeps_serial_and_quotes_device_shell():
    with patch('subprocess.run') as run:
        run.return_value = subprocess.CompletedProcess([], 0, 'ok', '')
        adb = Adb(serial='emulator-5554')
        adb.shell('input', 'text', "hello; reboot")
        assert run.call_args.args[0] == ['adb', '-s', 'emulator-5554', 'shell', "input text 'hello; reboot'"]
        assert run.call_args.kwargs['check'] is True
        assert run.call_args.kwargs['timeout'] == 30


def test_route_is_deterministic_and_ends_at_destination(tmp_path):
    route = tmp_path / 'route.gpx'
    route.write_text('<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
                     '<trkpt lat="40" lon="-73"/><trkpt lat="40.0001" lon="-73"/>'
                     '</trkseg></trk></gpx>')
    points = read_gpx(route)
    result = list(updates(points, 1.4))
    assert result == list(updates(points, 1.4))
    assert result[-1][0] == points[-1]
    assert sum(delay for _, delay in result) == pytest.approx(distance(*points) / 1.4)


@pytest.mark.parametrize('speed', [0, -1, float('nan'), float('inf')])
def test_bad_speed_is_rejected(speed):
    with pytest.raises(ValueError):
        list(updates([Point(0, 0)], speed))


def test_empty_route_is_rejected(tmp_path):
    route = tmp_path / 'empty.gpx'
    route.write_text('<gpx/>')
    with pytest.raises(ValueError, match='no track'):
        read_gpx(route)


def test_other_app_component_is_rejected():
    with pytest.raises(ValueError):
        component('com.other.app/.MainActivity', 'com.example.app')


def test_failed_launch_still_writes_report(tmp_path):
    cfg = load(Path(__file__).resolve().parents[2] / 'config/default.yaml')
    with patch('orchestrator.cli.wait_ready'), patch.object(Adb, 'shell', return_value=''):
        with patch.object(Adb, 'run', return_value=''):
            with pytest.raises(RuntimeError, match='not installed'):
                smoke(Adb(), cfg, tmp_path)
    assert 'failures="1"' in (tmp_path / 'junit.xml').read_text()
    assert (tmp_path / 'meta.json').exists()


@pytest.mark.parametrize('xml', ['<gpx>', '<gpx><wpt lon="0"/></gpx>', '<gpx><wpt lat="0" lon="0"><ele/></wpt></gpx>'])
def test_malformed_gpx_is_an_actionable_error(xml, tmp_path):
    route = tmp_path / 'bad.gpx'
    route.write_text(xml)
    with pytest.raises(ValueError, match='GPX'):
        read_gpx(route)


def test_bad_route_does_not_truncate_previous_trace(tmp_path):
    route = tmp_path / 'bad.gpx'
    route.write_text('<gpx/>')
    trace = tmp_path / 'trace.csv'
    trace.write_text('previous result')
    with pytest.raises(ValueError):
        follow(Adb(), route, 1, trace)
    assert trace.read_text() == 'previous result'


def test_route_schedule_accounts_for_adb_latency(tmp_path):
    now = [0.0]
    sent = []
    def sleep(duration):
        now[0] += duration
    def send(*args):
        sent.append(now[0])
        now[0] += 0.2
    points = [Point(0, 0), Point(0, 0.001), Point(0, 0.002)]
    with patch('orchestrator.location.read_gpx', return_value=points), \
         patch('orchestrator.location.updates', return_value=iter(zip(points, (0, 1, 1)))), \
         patch('orchestrator.location.time.monotonic', side_effect=lambda: now[0]), \
         patch('orchestrator.location.time.sleep', side_effect=sleep), \
         patch('orchestrator.location.set_location', side_effect=send):
        follow(Adb(), tmp_path / 'route.gpx', 1, tmp_path / 'trace.csv')
    assert sent == pytest.approx([0, 1, 2])
