"""Proxmox VE client for Android VM lifecycle management.

This module provides a minimal but complete Proxmox API client focused on
Android VM operations. It handles authentication, VM creation/cloning,
configuration, lifecycle operations, and task polling.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

import requests


@dataclass(frozen=True)
class VmConfig:
    """Configuration for creating or cloning an Android VM."""
    vm_id: int
    name: str
    cores: int = 4
    memory_mb: int = 8192
    cpu_type: str = "host"
    machine_type: str = "q35"
    bios: str = "seabios"
    disk_size_gb: int = 64
    disk_storage: str = "local"
    network_bridge: str = "vmbr0"
    network_model: str = "virtio"
    vga: str = "std"
    cdrom_iso: str | None = None
    node: str = "pve"

    def to_clone_params(self) -> dict[str, Any]:
        """Convert to Proxmox clone API parameters."""
        params: dict[str, Any] = {
            "newid": self.vm_id,
            "name": self.name,
            "full": 1,
        }
        return params

    def to_config_params(self) -> dict[str, Any]:
        """Convert to Proxmox config API parameters."""
        params: dict[str, Any] = {
            "cores": self.cores,
            "memory": self.memory_mb // 1024,  # Proxmox expects GB
            "cpu": self.cpu_type,
            "machine": self.machine_type,
            "bios": self.bios,
            f"{self.disk_storage}0": f"{self.disk_storage}:{self.disk_size_gb},format=qcow2",
            f"net0": f"{self.network_model},bridge={self.network_bridge}",
            "vga": self.vga,
            "boot": "order=sata0",
        }
        if self.cdrom_iso:
            params["cdrom"] = self.cdrom_iso
        return params


@dataclass
class VmStatus:
    """Current status of a VM."""
    vm_id: int
    status: str  # running, stopped, paused
    cpu_count: int = 0
    memory_mb: int = 0
    uptime_seconds: int = 0
    pid: int | None = None
    qmp_status: str | None = None

    @property
    def is_running(self) -> bool:
        return self.status == "running"

    @property
    def is_stopped(self) -> bool:
        return self.status == "stopped"


@dataclass
class TaskResult:
    """Result of a Proxmox task operation."""
    upid: str
    status: str  # OK, ERROR, TIMEOUT
    exit_code: str = ""
    message: str = ""
    duration_seconds: float = 0.0
    node: str = ""


class ProxmoxError(Exception):
    """Base exception for Proxmox operations."""


class AuthenticationError(ProxmoxError):
    """Raised when authentication fails."""


class VmNotFoundError(ProxmoxError):
    """Raised when a VM does not exist."""


class TaskTimeoutError(ProxmoxError):
    """Raised when waiting for a task times out."""


class ProxmoxClient:
    """Proxmox VE API client for Android VM management."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        realm: str = "pam",
        verify_ssl: bool = False,
        timeout: float = 30.0,
    ):
        """Initialize Proxmox client.

        Args:
            host: Proxmox server hostname or IP
            username: Username (e.g., 'root@pam')
            password: Password
            realm: Authentication realm (default: 'pam')
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
        """
        self.host = host
        self.base_url = f"https://{host}:8006/api2/json"
        self.timeout = timeout

        self.session = requests.Session()
        self.session.verify = verify_ssl
        self._authenticate(username, password, realm)

    def _authenticate(self, username: str, password: str, realm: str) -> None:
        """Authenticate and set session headers."""
        try:
            response = self.session.post(
                f"{self.base_url}/access/ticket",
                data={
                    "username": f"{username}@{realm}" if "@" not in username else username,
                    "password": password,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if "data" not in data:
                raise AuthenticationError("No ticket data in response")

            ticket_data = data["data"]
            self.session.headers.update({
                "Authorization": f"PVEAPITicket={ticket_data['ticket']}",
                "CSRFPreventionToken": ticket_data["CSRFPreventionToken"],
            })
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Failed to authenticate: {e}")

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated API request."""
        url = urljoin(self.base_url, path)

        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=self.timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, data=data, timeout=self.timeout)
            elif method.upper() == "PUT":
                response = self.session.put(url, data=data, timeout=self.timeout)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                raise ProxmoxError(f"API errors: {result['errors']}")

            return result

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise VmNotFoundError(f"Resource not found: {path}")
            raise ProxmoxError(f"HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            raise ProxmoxError(f"Request failed: {e}")

    def _get_task_status(self, node: str, upid: str) -> dict[str, Any]:
        """Get the status of a task by UPID."""
        result = self._request("GET", f"/nodes/{node}/tasks/{upid}/status")
        return result.get("data", {})

    def _wait_for_task(
        self,
        node: str,
        upid: str,
        timeout_s: float = 300.0,
        poll_interval: float = 1.0,
    ) -> TaskResult:
        """Wait for a Proxmox task to complete.

        Args:
            node: Proxmox node name
            upid: Unique task ID
            timeout_s: Maximum wait time in seconds
            poll_interval: Polling interval in seconds

        Returns:
            TaskResult with status and details
        """
        deadline = time.monotonic() + timeout_s
        start_time = time.monotonic()

        while time.monotonic() < deadline:
            status_data = self._get_task_status(node, upid)

            if status_data.get("status") == "STOPTIME":
                duration = status_data.get("duration", 0.0)
                exit_code = status_data.get("exitcode", "")

                return TaskResult(
                    upid=upid,
                    status="OK" if exit_code == "OK" else "ERROR",
                    exit_code=exit_code,
                    message=status_data.get("message", ""),
                    duration_seconds=duration,
                    node=node,
                )

            time.sleep(poll_interval)

        raise TaskTimeoutError(f"Task {upid} did not complete within {timeout_s}s")

    def check_connection(self) -> dict[str, Any]:
        """Verify connection to Proxmox server."""
        result = self._request("GET", "/cluster/status")
        return result.get("data", {})

    def get_vm_config(self, vm_id: int, node: str = "pve") -> dict[str, Any]:
        """Get current configuration for a VM."""
        result = self._request("GET", f"/nodes/{node}/qemu/{vm_id}/config")
        return result.get("data", {})

    def get_vm_status(self, vm_id: int, node: str = "pve") -> VmStatus:
        """Get current status of a VM."""
        result = self._request("GET", f"/nodes/{node}/qemu/{vm_id}/status/current")
        data = result.get("data", {})

        return VmStatus(
            vm_id=vm_id,
            status=data.get("status", "unknown"),
            cpu_count=data.get("cpus", 0),
            memory_mb=data.get("maxmem", 0) // (1024 * 1024),
            uptime_seconds=int(data.get("uptime", 0)),
            pid=data.get("pid"),
            qmp_status=data.get("qmpstatus"),
        )

    def clone_vm(
        self,
        template_id: int,
        config: VmConfig,
        node: str = "pve",
        timeout_s: float = 600.0,
    ) -> TaskResult:
        """Clone a VM from a template.

        Args:
            template_id: Source template VM ID
            config: Configuration for the new VM
            node: Proxmox node name
            timeout_s: Maximum wait time for clone operation

        Returns:
            TaskResult indicating success or failure
        """
        data = config.to_clone_params()

        result = self._request(
            "POST",
            f"/nodes/{node}/qemu/{template_id}/clone",
            data=data,
        )

        upid = result.get("data")
        if not upid:
            raise ProxmoxError("Clone operation did not return a UPID")

        return self._wait_for_task(node, upid, timeout_s=timeout_s)

    def create_vm(
        self,
        config: VmConfig,
        node: str = "pve",
    ) -> None:
        """Create a new VM from scratch.

        Args:
            config: VM configuration
            node: Proxmox node name
        """
        data = {
            "vmid": config.vm_id,
            "name": config.name,
            "cores": config.cores,
            "memory": config.memory_mb // 1024,
            "cpu": config.cpu_type,
            "machine": config.machine_type,
            "bios": config.bios,
            "net0": f"{config.network_model},bridge={config.network_bridge}",
            "vga": config.vga,
            "boot": "order=sata0",
        }

        if config.cdrom_iso:
            data["cdrom"] = config.cdrom_iso

        self._request("POST", f"/nodes/{node}/qemu", data=data)

        # Configure disk after VM creation
        disk_data = {
            f"{config.disk_storage}0": f"{config.disk_storage}:{config.disk_size_gb},format=qcow2",
        }
        self._request(
            "PUT",
            f"/nodes/{node}/qemu/{config.vm_id}/config",
            data=disk_data,
        )

    def configure_vm(
        self,
        vm_id: int,
        config: VmConfig,
        node: str = "pve",
    ) -> None:
        """Update VM configuration.

        Args:
            vm_id: VM ID to configure
            config: New configuration values
            node: Proxmox node name
        """
        data = config.to_config_params()
        self._request("PUT", f"/nodes/{node}/qemu/{vm_id}/config", data=data)

    def start_vm(
        self,
        vm_id: int,
        node: str = "pve",
        timeout_s: float = 120.0,
    ) -> TaskResult:
        """Start a VM.

        Args:
            vm_id: VM ID to start
            node: Proxmox node name
            timeout_s: Maximum wait time

        Returns:
            TaskResult indicating success or failure
        """
        result = self._request("POST", f"/nodes/{node}/qemu/{vm_id}/status/start")
        upid = result.get("data")

        if not upid:
            raise ProxmoxError("Start operation did not return a UPID")

        return self._wait_for_task(node, upid, timeout_s=timeout_s)

    def stop_vm(
        self,
        vm_id: int,
        node: str = "pve",
        timeout_s: float = 120.0,
        force: bool = False,
    ) -> TaskResult:
        """Stop a VM.

        Args:
            vm_id: VM ID to stop
            node: Proxmox node name
            timeout_s: Maximum wait time
            force: Use hard stop instead of ACPI shutdown

        Returns:
            TaskResult indicating success or failure
        """
        endpoint = "stop" if force else "shutdown"
        result = self._request("POST", f"/nodes/{node}/qemu/{vm_id}/status/{endpoint}")
        upid = result.get("data")

        if not upid:
            raise ProxmoxError("Stop operation did not return a UPID")

        return self._wait_for_task(node, upid, timeout_s=timeout_s)

    def reboot_vm(
        self,
        vm_id: int,
        node: str = "pve",
        timeout_s: float = 180.0,
    ) -> TaskResult:
        """Reboot a VM.

        Args:
            vm_id: VM ID to reboot
            node: Proxmox node name
            timeout_s: Maximum wait time

        Returns:
            TaskResult indicating success or failure
        """
        result = self._request("POST", f"/nodes/{node}/qemu/{vm_id}/status/reboot")
        upid = result.get("data")

        if not upid:
            raise ProxmoxError("Reboot operation did not return a UPID")

        return self._wait_for_task(node, upid, timeout_s=timeout_s)

    def delete_vm(
        self,
        vm_id: int,
        node: str = "pve",
        timeout_s: float = 120.0,
    ) -> TaskResult:
        """Delete a VM.

        Args:
            vm_id: VM ID to delete
            node: Proxmox node name
            timeout_s: Maximum wait time

        Returns:
            TaskResult indicating success or failure
        """
        result = self._request("DELETE", f"/nodes/{node}/qemu/{vm_id}")
        upid = result.get("data")

        if not upid:
            raise ProxmoxError("Delete operation did not return a UPID")

        return self._wait_for_task(node, upid, timeout_s=timeout_s)

    def convert_to_template(
        self,
        vm_id: int,
        node: str = "pve",
        timeout_s: float = 300.0,
    ) -> TaskResult:
        """Convert a VM to a template.

        Args:
            vm_id: VM ID to convert
            node: Proxmox node name
            timeout_s: Maximum wait time

        Returns:
            TaskResult indicating success or failure
        """
        result = self._request("POST", f"/nodes/{node}/qemu/{vm_id}/template")
        upid = result.get("data")

        if not upid:
            raise ProxmoxError("Template conversion did not return a UPID")

        return self._wait_for_task(node, upid, timeout_s=timeout_s)

    def list_vms(self, node: str = "pve") -> list[dict[str, Any]]:
        """List all VMs on a node.

        Args:
            node: Proxmox node name

        Returns:
            List of VM information dictionaries
        """
        result = self._request("GET", f"/nodes/{node}/qemu")
        return result.get("data", [])
