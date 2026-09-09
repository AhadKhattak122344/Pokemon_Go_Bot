"""Unit tests for Proxmox client module."""
import pytest
import requests
from unittest.mock import Mock, patch, PropertyMock

from orchestrator.proxmox import (
    ProxmoxClient,
    VmConfig,
    VmStatus,
    TaskResult,
    ProxmoxError,
    AuthenticationError,
    VmNotFoundError,
    TaskTimeoutError,
)


class TestVmConfig:
    """Tests for VmConfig dataclass."""

    def test_default_values(self):
        config = VmConfig(vm_id=100, name="test-vm")
        assert config.vm_id == 100
        assert config.name == "test-vm"
        assert config.cores == 4
        assert config.memory_mb == 8192
        assert config.cpu_type == "host"
        assert config.machine_type == "q35"
        assert config.bios == "seabios"
        assert config.disk_size_gb == 64
        assert config.disk_storage == "local"
        assert config.network_bridge == "vmbr0"
        assert config.network_model == "virtio"
        assert config.vga == "std"
        assert config.cdrom_iso is None

    def test_to_clone_params(self):
        config = VmConfig(vm_id=101, name="cloned-vm")
        params = config.to_clone_params()
        assert params["newid"] == 101
        assert params["name"] == "cloned-vm"
        assert params["full"] == 1

    def test_to_config_params(self):
        config = VmConfig(
            vm_id=102,
            name="configured-vm",
            cores=8,
            memory_mb=16384,
            cpu_type="x86-64-v2-AES",
            disk_storage="local-lvm",
            network_bridge="vmbr1",
        )
        params = config.to_config_params()
        assert params["cores"] == 8
        assert params["memory"] == 16  # GB
        assert params["cpu"] == "x86-64-v2-AES"
        assert params["machine"] == "q35"
        assert params["bios"] == "seabios"
        assert "local-lvm0" in params
        assert "local-lvm:64,format=qcow2" in params["local-lvm0"]
        assert params["net0"] == "virtio,bridge=vmbr1"
        assert params["vga"] == "std"
        assert params["boot"] == "order=sata0"

    def test_to_config_params_with_cdrom(self):
        config = VmConfig(
            vm_id=103,
            name="install-vm",
            cdrom_iso="local:iso/Bliss-v16.9.7.iso",
        )
        params = config.to_config_params()
        assert params["cdrom"] == "local:iso/Bliss-v16.9.7.iso"


class TestVmStatus:
    """Tests for VmStatus dataclass."""

    def test_is_running_property(self):
        status = VmStatus(vm_id=100, status="running")
        assert status.is_running is True
        assert status.is_stopped is False

    def test_is_stopped_property(self):
        status = VmStatus(vm_id=100, status="stopped")
        assert status.is_stopped is True
        assert status.is_running is False

    def test_status_with_full_data(self):
        status = VmStatus(
            vm_id=100,
            status="running",
            cpu_count=4,
            memory_mb=8192,
            uptime_seconds=3600,
            pid=12345,
            qmp_status="running",
        )
        assert status.vm_id == 100
        assert status.cpu_count == 4
        assert status.memory_mb == 8192
        assert status.uptime_seconds == 3600
        assert status.pid == 12345
        assert status.qmp_status == "running"


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_default_values(self):
        result = TaskResult(upid="UPID:123", status="OK")
        assert result.upid == "UPID:123"
        assert result.status == "OK"
        assert result.exit_code == ""
        assert result.message == ""
        assert result.duration_seconds == 0.0
        assert result.node == ""

    def test_successful_result(self):
        result = TaskResult(
            upid="UPID:abc",
            status="OK",
            exit_code="OK",
            duration_seconds=120.5,
            node="pve",
        )
        assert result.status == "OK"
        assert result.exit_code == "OK"
        assert result.duration_seconds == 120.5


class TestProxmoxClientAuthentication:
    """Tests for ProxmoxClient authentication."""

    @patch("orchestrator.proxmox.requests.Session")
    def test_successful_authentication(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "ticket": "test-ticket",
                "CSRFPreventionToken": "test-csrf-token",
            }
        }
        mock_session.post.return_value = mock_response

        client = ProxmoxClient(
            host="proxmox.example.com",
            username="root",
            password="secret",
        )

        # Verify authentication was called correctly
        call_args = mock_session.post.call_args_list[0]
        assert "access/ticket" in call_args.args[0]
        assert call_args.kwargs["data"]["username"] == "root@pam"
        assert call_args.kwargs["data"]["password"] == "secret"

        # Verify headers were set
        mock_session.headers.update.assert_called_once()

    @patch("orchestrator.proxmox.requests.Session")
    def test_authentication_failure(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.post.side_effect = requests.exceptions.RequestException("Connection refused")

        with pytest.raises(AuthenticationError):
            ProxmoxClient(
                host="proxmox.example.com",
                username="root",
                password="wrong-password",
            )

    @patch("orchestrator.proxmox.requests.Session")
    def test_authentication_with_realm(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "ticket": "test-ticket",
                "CSRFPreventionToken": "test-csrf-token",
            }
        }
        mock_session.post.return_value = mock_response

        client = ProxmoxClient(
            host="proxmox.example.com",
            username="admin",
            password="secret",
            realm="pve",
        )

        call_args = mock_session.post.call_args_list[0]
        assert call_args.kwargs["data"]["username"] == "admin@pve"


class TestProxmoxClientVmOperations:
    """Tests for VM operations."""

    def _create_mock_client(self, mock_session_class):
        """Helper to create a mocked client."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Setup auth response
        auth_response = Mock()
        auth_response.json.return_value = {
            "data": {
                "ticket": "test-ticket",
                "CSRFPreventionToken": "test-csrf-token",
            }
        }
        mock_session.post.return_value = auth_response

        client = ProxmoxClient(
            host="proxmox.example.com",
            username="root",
            password="secret",
        )
        return client, mock_session

    @patch("orchestrator.proxmox.requests.Session")
    def test_check_connection(self, mock_session_class):
        client, mock_session = self._create_mock_client(mock_session_class)

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"type": "node", "name": "pve", "status": "online"},
            ]
        }
        mock_session.get.return_value = mock_response

        result = client.check_connection()
        assert len(result) == 1
        assert result[0]["name"] == "pve"

    @patch("orchestrator.proxmox.requests.Session")
    def test_get_vm_status(self, mock_session_class):
        client, mock_session = self._create_mock_client(mock_session_class)

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "status": "running",
                "cpus": 4,
                "maxmem": 8589934592,  # 8GB in bytes
                "uptime": 3600,
                "pid": 12345,
                "qmpstatus": "running",
            }
        }
        mock_session.get.return_value = mock_response

        status = client.get_vm_status(100)
        assert status.vm_id == 100
        assert status.status == "running"
        assert status.cpu_count == 4
        assert status.memory_mb == 8192
        assert status.uptime_seconds == 3600
        assert status.is_running is True

    @patch("orchestrator.proxmox.requests.Session")
    def test_get_vm_status_stopped(self, mock_session_class):
        client, mock_session = self._create_mock_client(mock_session_class)

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "status": "stopped",
                "cpus": 0,
                "maxmem": 0,
                "uptime": 0,
            }
        }
        mock_session.get.return_value = mock_response

        status = client.get_vm_status(100)
        assert status.status == "stopped"
        assert status.is_stopped is True

    @patch("orchestrator.proxmox.requests.Session")
    def test_get_vm_config(self, mock_session_class):
        client, mock_session = self._create_mock_client(mock_session_class)

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "cores": 4,
                "memory": 8192,
                "cpu": "host",
                "net0": "virtio,bridge=vmbr0",
            }
        }
        mock_session.get.return_value = mock_response

        config = client.get_vm_config(100)
        assert config["cores"] == 4
        assert config["memory"] == 8192

    @patch("orchestrator.proxmox.requests.Session")
    def test_start_vm(self, mock_session_class):
        client, mock_session = self._create_mock_client(mock_session_class)

        # Setup start response with UPID
        start_response = Mock()
        start_response.json.return_value = {
            "data": "UPID:pve:00001234:0000ABCD:start::"
        }
        mock_session.post.return_value = start_response

        # Setup task status responses (first pending, then complete)
        task_response_pending = Mock()
        task_response_pending.json.return_value = {
            "data": {"status": "RUNNING"}
        }

        task_response_complete = Mock()
        task_response_complete.json.return_value = {
            "data": {
                "status": "STOPTIME",
                "exitcode": "OK",
                "duration": 5.2,
            }
        }

        mock_session.get.side_effect = [
            task_response_pending,
            task_response_complete,
        ]

        result = client.start_vm(100)
        assert result.upid == "UPID:pve:00001234:0000ABCD:start::"
        assert result.status == "OK"
        assert result.exit_code == "OK"

    @patch("orchestrator.proxmox.requests.Session")
    def test_stop_vm_force(self, mock_session_class):
        client, mock_session = self._create_mock_client(mock_session_class)

        stop_response = Mock()
        stop_response.json.return_value = {
            "data": "UPID:pve:00001234:0000ABCD:stop::"
        }
        mock_session.post.return_value = stop_response

        task_response = Mock()
        task_response.json.return_value = {
            "data": {"status": "STOPTIME", "exitcode": "OK"}
        }
        mock_session.get.return_value = task_response

        result = client.stop_vm(100, force=True)
        assert result.status == "OK"

        # Verify 'stop' endpoint was used, not 'shutdown'
        call_args = mock_session.post.call_args_list[1]
        assert "status/stop" in call_args.args[0]

    @patch("orchestrator.proxmox.requests.Session")
    def test_stop_vm_graceful(self, mock_session_class):
        client, mock_session = self._create_mock_client(mock_session_class)

        stop_response = Mock()
        stop_response.json.return_value = {
            "data": "UPID:pve:00001234:0000ABCD:shutdown::"
        }
        mock_session.post.return_value = stop_response

        task_response = Mock()
        task_response.json.return_value = {
            "data": {"status": "STOPTIME", "exitcode": "OK"}
        }
        mock_session.get.return_value = task_response

        result = client.stop_vm(100, force=False)
        assert result.status == "OK"

        # Verify 'shutdown' endpoint was used
        call_args = mock_session.post.call_args_list[1]
        assert "status/shutdown" in call_args.args[0]

    @patch("orchestrator.proxmox.requests.Session")
    def test_reboot_vm(self, mock_session_class):
        client, mock_session = self._create_mock_client(mock_session_class)

        reboot_response = Mock()
        reboot_response.json.return_value = {
            "data": "UPID:pve:00001234:0000ABCD:reboot::"
        }
        mock_session.post.return_value = reboot_response

        task_response = Mock()
        task_response.json.return_value = {
            "data": {"status": "STOPTIME", "exitcode": "OK"}
        }
        mock_session.get.return_value = task_response

        result = client.reboot_vm(100)
        assert result.status == "OK"

    @patch("orchestrator.proxmox.requests.Session")
    def test_delete_vm(self, mock_session_class):
        client, mock_session = self._create_mock_client(mock_session_class)

        delete_response = Mock()
        delete_response.json.return_value = {
            "data": "UPID:pve:00001234:0000ABCD:delete::"
        }
        mock_session.delete.return_value = delete_response

        task_response = Mock()
        task_response.json.return_value = {
            "data": {"status": "STOPTIME", "exitcode": "OK"}
        }
        mock_session.get.return_value = task_response

        result = client.delete_vm(100)
        assert result.status == "OK"

    @patch("orchestrator.proxmox.requests.Session")
    def test_list_vms(self, mock_session_class):
        client, mock_session = self._create_mock_client(mock_session_class)

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"vmid": 100, "name": "vm1", "status": "running"},
                {"vmid": 101, "name": "vm2", "status": "stopped"},
            ]
        }
        mock_session.get.return_value = mock_response

        vms = client.list_vms()
        assert len(vms) == 2
        assert vms[0]["vmid"] == 100
        assert vms[1]["vmid"] == 101


class TestProxmoxClientCloneVm:
    """Tests for VM cloning operations."""

    @patch("orchestrator.proxmox.requests.Session")
    def test_clone_vm(self, mock_session_class):
        client, mock_session = self._create_mock_client_for_clone(mock_session_class)

        config = VmConfig(vm_id=101, name="cloned-android")
        result = client.clone_vm(template_id=9000, config=config)

        # Verify clone was called with correct parameters
        clone_call = mock_session.post.call_args_list[1]
        assert "qemu/9000/clone" in clone_call.args[0]
        assert clone_call.kwargs["data"]["newid"] == 101
        assert clone_call.kwargs["data"]["name"] == "cloned-android"
        assert clone_call.kwargs["data"]["full"] == 1

        assert result.status == "OK"

    @classmethod
    def _create_mock_client_for_clone(cls, mock_session_class):
        """Helper to create client configured for clone tests."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Auth response
        auth_response = Mock()
        auth_response.json.return_value = {
            "data": {"ticket": "ticket", "CSRFPreventionToken": "token"}
        }
        mock_session.post.return_value = auth_response

        client = ProxmoxClient("proxmox.example.com", "root", "secret")

        # Clone response
        clone_response = Mock()
        clone_response.json.return_value = {
            "data": "UPID:pve:00001234:0000ABCD:clone::"
        }
        mock_session.post.return_value = clone_response

        # Task status
        task_response = Mock()
        task_response.json.return_value = {
            "data": {"status": "STOPTIME", "exitcode": "OK"}
        }
        mock_session.get.return_value = task_response

        return client, mock_session

    @staticmethod
    def _create_mock_client_for_clone(mock_session_class):
        """Helper to create client configured for clone tests."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Auth response
        auth_response = Mock()
        auth_response.json.return_value = {
            "data": {"ticket": "ticket", "CSRFPreventionToken": "token"}
        }
        mock_session.post.return_value = auth_response

        client = ProxmoxClient("proxmox.example.com", "root", "secret")

        # Clone response
        clone_response = Mock()
        clone_response.json.return_value = {
            "data": "UPID:pve:00001234:0000ABCD:clone::"
        }
        mock_session.post.return_value = clone_response

        # Task status
        task_response = Mock()
        task_response.json.return_value = {
            "data": {"status": "STOPTIME", "exitcode": "OK"}
        }
        mock_session.get.return_value = task_response

        return client, mock_session


class TestProxmoxClientTaskWaiting:
    """Tests for task waiting behavior."""

    @patch("orchestrator.proxmox.requests.Session")
    def test_task_timeout(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Auth
        auth_response = Mock()
        auth_response.json.return_value = {
            "data": {"ticket": "ticket", "CSRFPreventionToken": "token"}
        }
        mock_session.post.return_value = auth_response

        client = ProxmoxClient("proxmox.example.com", "root", "secret")

        # Start response
        start_response = Mock()
        start_response.json.return_value = {"data": "UPID:test"}
        mock_session.post.return_value = start_response

        # Task always pending
        task_response = Mock()
        task_response.json.return_value = {"data": {"status": "RUNNING"}}
        mock_session.get.return_value = task_response

        with pytest.raises(TaskTimeoutError):
            client.start_vm(100, timeout_s=0.1)

    @patch("orchestrator.proxmox.requests.Session")
    def test_task_error_exit_code(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Auth
        auth_response = Mock()
        auth_response.json.return_value = {
            "data": {"ticket": "ticket", "CSRFPreventionToken": "token"}
        }
        mock_session.post.return_value = auth_response

        client = ProxmoxClient("proxmox.example.com", "root", "secret")

        # Start response
        start_response = Mock()
        start_response.json.return_value = {"data": "UPID:test"}
        mock_session.post.return_value = start_response

        # Task completed with error
        task_response = Mock()
        task_response.json.return_value = {
            "data": {"status": "STOPTIME", "exitcode": "ERROR"}
        }
        mock_session.get.return_value = task_response

        result = client.start_vm(100)
        assert result.status == "ERROR"
        assert result.exit_code == "ERROR"


class TestProxmoxClientErrors:
    """Tests for error handling."""

    @patch("orchestrator.proxmox.requests.Session")
    def test_vm_not_found(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Auth
        auth_response = Mock()
        auth_response.json.return_value = {
            "data": {"ticket": "ticket", "CSRFPreventionToken": "token"}
        }
        mock_session.post.return_value = auth_response

        client = ProxmoxClient("proxmox.example.com", "root", "secret")

        # 404 response
        from requests.exceptions import HTTPError
        mock_session.get.side_effect = HTTPError(response=Mock(status_code=404))

        with pytest.raises(VmNotFoundError):
            client.get_vm_status(999)

    @patch("orchestrator.proxmox.requests.Session")
    def test_api_errors_in_response(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Auth
        auth_response = Mock()
        auth_response.json.return_value = {
            "data": {"ticket": "ticket", "CSRFPreventionToken": "token"}
        }
        mock_session.post.return_value = auth_response

        client = ProxmoxClient("proxmox.example.com", "root", "secret")

        # Response with errors
        error_response = Mock()
        error_response.json.return_value = {
            "errors": {"param": "invalid value"}
        }
        mock_session.get.return_value = error_response

        with pytest.raises(ProxmoxError):
            client.get_vm_status(100)
