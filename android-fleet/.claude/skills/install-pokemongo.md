---
name: install-pokemongo
description: Install Pokémon GO on an instance with all required spoofing modules and configuration
triggers:
  - /install-pokemon
  - /install-pokemongo
  - /setup-pokemon
  - /poke-install
parameters:
  - name: vm_id
    type: integer
    required: true
    description: Proxmox VM ID (e.g., 10001)
  - name: apk_path
    type: string
    required: false
    description: Path to Pokémon GO APK file (default: download latest from official source)
  - name: version
    type: string
    required: false
    default: "latest"
    description: Pokémon GO version to install
actions:
  - Validate VM exists and is running
  - Get VM IP address and connect via ADB
  - Verify device fingerprint is set to Pixel 4
  - Verify Magisk modules are installed:
    - Zygisk Next
    - Shamiko
    - Play Integrity Fix
    - libhoudini
  - Download Pokémon GO APK if not provided:
    - Use APKMirror or official source
    - Verify checksum integrity
  - Install Pokémon GO via ADB:
    - adb install -r pokemon_go.apk
  - Configure DenyList in Magisk:
    - Add com.nianticlabs.pokemongo to DenyList
    - Enable Zygisk for Pokémon GO
  - Install GPS spoofing module (if needed):
    - Mock Location app or LSPosed module
  - Clear Pokémon GO data to reset state
  - Launch Pokémon GO to verify installation
  - Check for bans or soft bans
  - Send installation notification via ntfy
output: |
  ✅ Pokémon GO installed successfully!
  
  VM ID: {vm_id}
  Name: {vm_name}
  
  Installation Details:
  ├── Version: {version}
  ├── Package: com.nianticlabs.pokemongo
  ├── Size: {apk_size}MB
  └── Install Time: {install_time}s
  
  Spoofing Status:
  ├── Root Hidden: ✅ (Shamiko active)
  ├── Device Certified: ✅ (Pixel 4 fingerprint)
  ├── Play Integrity: ✅ (MEETS_DEVICE_INTEGRITY)
  ├── ARM Translation: ✅ (libhoudini active)
  └── GPS Spoofing: {gps_status}
  
  Launch Status: SUCCESS
  Ban Status: CLEAN ✅
  
  Ready to play! Connect via Scrcpy: scrcpy -s {ip}:5555
---
