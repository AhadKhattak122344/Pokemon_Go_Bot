---
name: deploy-instance
description: Deploy a new Android VM instance configured for Pokémon GO with unique identity, Pixel 4 fingerprint, and Magisk modules
triggers:
  - /deploy
  - /deploy-instance
  - /create-vm
  - /create-instance
parameters:
  - name: vm_name
    type: string
    required: true
    description: Unique name for the VM (e.g., pokemon-001)
  - name: template_id
    type: integer
    default: 9000
    description: Proxmox template ID (default: 9000 for Bliss OS)
  - name: node
    type: string
    default: proxmox
    description: Proxmox node name
actions:
  - Generate unique identity (Android ID, IMEI, MAC address, serial number)
  - Validate identity format and uniqueness against database
  - Clone VM from template via Proxmox API (POST /nodes/{node}/qemu/{template_id}/clone)
  - Apply unique MAC address to VM configuration
  - Start VM via Proxmox API (POST /nodes/{node}/qemu/{vmid}/status/start)
  - Wait for boot completion (monitor sys.boot_completed via ADB)
  - Connect via ADB over TCP (adb connect {ip}:5555)
  - Apply Pixel 4 device fingerprint using MagiskHide Props Config
  - Set unique Android ID, IMEI, and serial via LSPosed/Device Emulator
  - Clear Google Services data (com.google.android.gms, com.google.android.gsf, com.android.vending)
  - Reboot VM to apply all changes
  - Verify Play Store certification status
  - Register instance in PostgreSQL database (instances + identity_profiles tables)
  - Send deployment notification via ntfy to android-fleet-events topic
output: |
  ✅ Instance deployed successfully!
  
  VM ID: {vm_id}
  Name: {vm_name}
  IP: {ip_address}
  Android ID: {android_id}
  IMEI: {imei}
  MAC: {mac_address}
  Status: RUNNING
  Play Store: CERTIFIED
  
  Connect via ADB: adb connect {ip_address}:5555
  View in Scrcpy: scrcpy -s {ip_address}:5555
---
