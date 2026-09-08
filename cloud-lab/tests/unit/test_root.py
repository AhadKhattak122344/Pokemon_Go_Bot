import subprocess
from unittest.mock import Mock, patch

import pytest

from orchestrator.root import RootManager, RootStatus


def state(uid=2000, emulator=True, debug=True):
    return RootStatus('emulator-5554', uid, uid == 0, emulator, debug,
                      'userdebug', 'x86', 'Enforcing', None, None, [])


def test_status_never_tries_su_or_enables_root():
    adb = Mock(serial='emulator-5554')
    props = '[ro.kernel.qemu]: [1]\n[ro.debuggable]: [1]\n[ro.product.cpu.abilist]: [x86]'
    def shell(*args, **kwargs):
        if args == ('id', '-u'): return '2000'
        if args == ('getprop',): return props
        if args == ('getenforce',): return 'Enforcing'
        raise subprocess.CalledProcessError(1, args)
    adb.shell.side_effect = shell
    result = RootManager(adb).status()
    assert result.adb_root is False
    assert result.emulator and result.debuggable
    assert result.modules is None
    assert result.magisk_binary is None
    adb.run.assert_not_called()
    assert all('su' not in c.args for c in adb.shell.call_args_list)


@pytest.mark.parametrize('status', [state(emulator=False), state(debug=False)])
def test_unsupported_enable_is_rejected_before_mutation(status):
    adb = Mock()
    manager = RootManager(adb)
    with patch.object(manager, 'status', return_value=status):
        with pytest.raises(RuntimeError): manager.set_enabled(True)
    adb.run.assert_not_called()


def test_enable_waits_for_reconnect_and_verifies_uid():
    adb = Mock()
    adb.run.return_value = 'restarting adbd as root'
    adb.shell.side_effect = [subprocess.CalledProcessError(1, []), '0']
    manager = RootManager(adb)
    with patch.object(manager, 'status', side_effect=[state(), state(0)]), patch('time.sleep'):
        result = manager.set_enabled(True)
    assert result['after']['adb_uid'] == 0
    adb.run.assert_called_once_with('root', timeout=10)


def test_false_success_output_is_rejected():
    adb = Mock()
    adb.run.return_value = 'adbd cannot run as root in production builds'
    manager = RootManager(adb)
    with patch.object(manager, 'status', return_value=state()):
        with pytest.raises(RuntimeError, match='rejected'): manager.set_enabled(True)


def test_roundtrip_restores_original_privilege_on_failure():
    manager = RootManager(Mock())
    with patch.object(manager, 'status', return_value=state(0)), \
         patch.object(manager, 'set_enabled', side_effect=[{}, RuntimeError('disconnect'), {}]) as change:
        with pytest.raises(RuntimeError, match='disconnect'): manager.roundtrip()
    assert [c.args[0] for c in change.call_args_list] == [True, False, True]


def test_already_correct_mode_is_idempotent():
    adb = Mock()
    manager = RootManager(adb)
    with patch.object(manager, 'status', return_value=state(0)):
        assert manager.set_enabled(True)['changed'] is False
    adb.run.assert_not_called()


def test_offline_device_is_not_reported_as_unrooted():
    adb = Mock()
    adb.shell.side_effect = subprocess.CalledProcessError(1, [])
    with pytest.raises(subprocess.CalledProcessError): RootManager(adb).status()


def test_wrong_uid_times_out_instead_of_reporting_success():
    adb = Mock()
    adb.run.return_value = 'restarting adbd as root'
    adb.shell.return_value = '2000'
    manager = RootManager(adb)
    with patch.object(manager, 'status', return_value=state()), patch('time.sleep'):
        with pytest.raises(TimeoutError): manager.set_enabled(True, timeout_s=0.01)
