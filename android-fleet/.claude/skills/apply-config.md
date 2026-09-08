---
name: apply-config
description: Apply Pokémon GO configuration to an instance including device fingerprint, identity, and app settings
triggers:
  - /config
  - /apply-config
  - /configure-instance
  - /set-fingerprint
parameters:
  - name: vm_id
    type: integer
    required: true
    description: Proxmox VM ID (e.g., 10001)
  - name: config_file
    type: string
    required: false
    description: Path to JSON configuration file
  - name: fingerprint
    type: string
    required: false
    default: "pixel4"
    description: Device fingerprint profile (pixel4, galaxy_s21, oneplus_9)
actions:
  - Validate VM exists and is running via Proxmox API
  - Get VM IP address from database or DHCP lease
  - Connect via ADB over TCP (adb connect {ip}:5555)
  - If config_file provided:
    - Load and validate JSON configuration
    - Extract identity (Android ID, IMEI, serial, model, manufacturer)
    - Extract fingerprint properties
  - Apply device fingerprint using MagiskHide Props Config:
    - Set ro.product.model
    - Set ro.product.manufacturer
    - Set ro.build.fingerprint
    - Set ro.build.description
    - Set ro.product.name
    - Set ro.product.device
    - Set ro.build.version.sdk
    - Set ro.build.version.release
  - Apply unique identity via LSPosed/Device Emulator:
    - Set Android ID in settings database
    - Set IMEI via system property
    - Set serial number
  - Clear Google Services data to force re-certification:
    - pm clear com.google.android.gms
    - pm clear com.google.android.gsf
    - pm clear com.android.vending
  - Reboot VM to apply all changes
  - Wait for reboot completion (adb wait-for-device)
  - Verify configuration applied correctly:
    - Check device fingerprint matches target
    - Verify Play Store certification status
    - Confirm unique identity is set
  - Update database with new configuration
  - Send configuration notification via ntfy
output: |
  ✅ Configuration applied successfully!
  
  VM ID: {vm_id}
  Name: {vm_name}
  
  Applied Fingerprint:
  ├── Model: {model}
  ├── Manufacturer: {manufacturer}
  ├── Android Version: {android_version}
  └── SDK Level: {sdk_level}
  
  Applied Identity:
  ├── Android ID: {android_id}
  ├── IMEI: {imei}
  └── Serial: {serial}
  
  Play Store Status: {play_store_status}
  Certification: {certification_status}
  
  Rebooted: Yes
  Verification: PASSED ✅
---
