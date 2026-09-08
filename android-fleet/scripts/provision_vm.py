#!/usr/bin/env python3
"""
Proxmox VM Provisioning Script for Android Fleet
Clones VMs from template and configures them with unique identities.
"""

import asyncio
import aiohttp
import ssl
import json
import argparse
import subprocess
import time
from typing import Optional, Dict, Any


class ProxmoxClient:
    """Async client for Proxmox REST API."""
    
    def __init__(self, host: str, username: str, password: str, node: str = "proxmox"):
        self.host = host
        self.node = node
        self.base_url = f"https://{host}:8006/api2/json"
        self.session = None
        self.token = None
        self.csrf_token = None
        self.username = username
        self.password = password
        
    async def __aenter__(self):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(connector=connector)
        await self.authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def authenticate(self):
        """Authenticate and get API ticket."""
        async with self.session.post(
            f"{self.base_url}/access/ticket",
            data={"username": self.username, "password": self.password}
        ) as response:
            response.raise_for_status()
            data = await response.json()
            ticket_data = data["data"]
            self.token = ticket_data["ticket"]
            self.csrf_token = ticket_data["CSRFPreventionToken"]
            self.session.headers.update({
                "Authorization": f"PVEAPITicket={self.token}",
                "CSRFPreventionToken": self.csrf_token
            })
            print(f"✓ Authenticated to Proxmox {self.host}")
    
    async def clone_vm(self, template_id: int, new_id: int, name: str, full: bool = True) -> dict:
        """Clone VM from template."""
        print(f"Cloning VM {template_id} → {new_id} ({name})...")
        async with self.session.post(
            f"{self.base_url}/nodes/{self.node}/qemu/{template_id}/clone",
            data={"newid": new_id, "name": name, "full": 1 if full else 0}
        ) as response:
            response.raise_for_status()
            result = await response.json()
            print(f"✓ Clone task started: {result.get('data', 'N/A')}")
            return result
    
    async def configure_vm(self, vm_id: int, **kwargs) -> dict:
        """Configure VM settings."""
        print(f"Configuring VM {vm_id}...")
        async with self.session.post(
            f"{self.base_url}/nodes/{self.node}/qemu/{vm_id}/config",
            data=kwargs
        ) as response:
            response.raise_for_status()
            result = await response.json()
            print(f"✓ Configuration applied")
            return result
    
    async def start_vm(self, vm_id: int) -> dict:
        """Start VM."""
        print(f"Starting VM {vm_id}...")
        async with self.session.post(
            f"{self.base_url}/nodes/{self.node}/qemu/{vm_id}/status/start"
        ) as response:
            response.raise_for_status()
            result = await response.json()
            print(f"✓ Start task started")
            return result
    
    async def stop_vm(self, vm_id: int) -> dict:
        """Stop VM."""
        print(f"Stopping VM {vm_id}...")
        async with self.session.post(
            f"{self.base_url}/nodes/{self.node}/qemu/{vm_id}/status/stop"
        ) as response:
            response.raise_for_status()
            result = await response.json()
            print(f"✓ Stop task started")
            return result
    
    async def destroy_vm(self, vm_id: int) -> dict:
        """Destroy VM."""
        print(f"Destroying VM {vm_id}...")
        async with self.session.delete(
            f"{self.base_url}/nodes/{self.node}/qemu/{vm_id}"
        ) as response:
            response.raise_for_status()
            result = await response.json()
            print(f"✓ VM destroyed")
            return result
    
    async def get_vm_status(self, vm_id: int) -> dict:
        """Get VM status."""
        async with self.session.get(
            f"{self.base_url}/nodes/{self.node}/qemu/{vm_id}/status/current"
        ) as response:
            response.raise_for_status()
            result = await response.json()
            return result.get("data", {})
    
    async def wait_for_vm_running(self, vm_id: int, timeout: int = 300) -> bool:
        """Wait for VM to be running."""
        print(f"Waiting for VM {vm_id} to start...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = await self.get_vm_status(vm_id)
            if status.get("status") == "running":
                print(f"✓ VM {vm_id} is running")
                return True
            await asyncio.sleep(2)
        print(f"✗ Timeout waiting for VM {vm_id}")
        return False
    
    async def list_vms(self) -> list:
        """List all VMs on node."""
        async with self.session.get(
            f"{self.base_url}/nodes/{self.node}/qemu"
        ) as response:
            response.raise_for_status()
            result = await response.json()
            return result.get("data", [])


async def apply_fingerprint_via_adb(ip: str, identity: dict, port: int = 5555):
    """Apply device fingerprint via ADB."""
    print(f"Applying fingerprint to {ip}:{port}...")
    
    # Connect via ADB
    subprocess.run(["adb", "connect", f"{ip}:{port}"], check=True, capture_output=True)
    time.sleep(2)
    
    # Apply properties
    props = {
        "ro.product.model": identity["model"],
        "ro.product.manufacturer": identity["manufacturer"],
        "ro.product.device": identity["device"],
        "ro.product.name": identity["name"],
        "ro.build.fingerprint": identity["fingerprint"],
        "ro.build.description": identity["description"],
        "ro.build.version.sdk": identity["sdk"],
        "ro.build.version.release": identity["release"]
    }
    
    for key, value in props.items():
        subprocess.run(
            ["adb", "shell", "su", "-c", f"setprop {key} \"{value}\""],
            capture_output=True
        )
    
    # Clear Google services to re-register with new fingerprint
    print("Clearing Google services cache...")
    subprocess.run(["adb", "shell", "pm", "clear", "com.google.android.gms"], capture_output=True)
    subprocess.run(["adb", "shell", "pm", "clear", "com.google.android.gsf"], capture_output=True)
    subprocess.run(["adb", "shell", "pm", "clear", "com.android.vending"], capture_output=True)
    
    print(f"✓ Fingerprint applied to {ip}")


async def provision_instance(
    proxmox_host: str,
    proxmox_user: str,
    proxmox_pass: str,
    template_id: int,
    identity: dict,
    vm_name: Optional[str] = None,
    vm_id: Optional[int] = None
) -> int:
    """Provision a single Android VM instance."""
    
    # Generate VM ID if not provided
    if vm_id is None:
        vm_id = 10000 + (hash(identity["android_id"]) % 1000)
    
    if vm_name is None:
        vm_name = identity["instance_name"]
    
    async with ProxmoxClient(proxmox_host, proxmox_user, proxmox_pass) as client:
        # Clone from template
        await client.clone_vm(template_id, vm_id, vm_name)
        
        # Wait for clone to complete (simplified - in production check task status)
        await asyncio.sleep(10)
        
        # Configure MAC address
        mac = identity["mac_address"]
        await client.configure_vm(vm_id, **{
            "net0": f"virtio,macaddr={mac},bridge=vmbr0"
        })
        
        # Start VM
        await client.start_vm(vm_id)
        
        # Wait for VM to be running
        await client.wait_for_vm_running(vm_id, timeout=120)
        
        print(f"\n✓ VM {vm_id} ({vm_name}) provisioned successfully")
        print(f"  MAC Address: {mac}")
        print(f"  Device Model: {identity['model']}")
        print(f"  Android ID: {identity['android_id']}")
        
        return vm_id


def main():
    parser = argparse.ArgumentParser(description="Provision Android VM on Proxmox")
    parser.add_argument("--host", required=True, help="Proxmox host")
    parser.add_argument("--user", required=True, help="Proxmox username")
    parser.add_argument("--password", required=True, help="Proxmox password")
    parser.add_argument("--node", default="proxmox", help="Proxmox node name")
    parser.add_argument("--template-id", type=int, default=9000, help="Template VM ID")
    parser.add_argument("--identity-file", required=True, help="JSON file with identity")
    parser.add_argument("--vm-id", type=int, help="VM ID (auto-generated if not provided)")
    parser.add_argument("--vm-name", type=str, help="VM name (auto-generated if not provided)")
    args = parser.parse_args()
    
    # Load identity
    with open(args.identity_file) as f:
        identity = json.load(f)
    
    # Run provisioning
    vm_id = asyncio.run(provision_instance(
        proxmox_host=args.host,
        proxmox_user=args.user,
        proxmox_pass=args.password,
        template_id=args.template_id,
        identity=identity,
        vm_id=args.vm_id,
        vm_name=args.vm_name
    ))
    
    print(f"\nProvisioning complete! VM ID: {vm_id}")


if __name__ == "__main__":
    main()
