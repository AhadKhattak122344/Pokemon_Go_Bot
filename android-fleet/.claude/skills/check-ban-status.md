---
name: check-ban-status
description: Check ban status for a Pokémon GO instance (soft ban, warning, permanent ban)
triggers:
  - /check-ban
  - /ban-status
  - /is-banned
  - /poke-status
parameters:
  - name: vm_id
    type: integer
    required: true
    description: Proxmox VM ID (e.g., 10001)
actions:
  - Validate VM exists and is running
  - Get VM IP address and connect via ADB
  - Launch Pokémon GO via ADB:
    adb shell am start -n com.nianticlabs.pokemongo/.UnityPlayerActivity
  - Monitor app behavior for ban indicators:
    - Soft ban: Pokémon flee immediately, PokéStops don't give items
    - Warning screen: Red warning message on login
    - Permanent ban: "Account terminated" or unable to login
  - Check Play Integrity API response:
    - MEETS_DEVICE_INTEGRITY = Clean
    - MEETS_STRONG_INTEGRITY = Clean + certified
    - DEVICE_NOT_INTEGRITY = Potential flag
  - Capture screenshot of game state
  - Analyze logs for ban-related messages
  - Send ban status notification via ntfy
output: |
  📋 Ban Status Report
  
  VM ID: {vm_id}
  Name: {vm_name}
  Account: {account_email}
  
  Status: {status}
  
  === Detection Results ===
  ├── Soft Ban: {soft_ban_status}
  ├── Warning: {warning_status}
  ├── Permanent Ban: {permaban_status}
  └── Play Integrity: {integrity_status}
  
  === Indicators ===
  {indicators_list}
  
  Last Checked: {timestamp}
  Screenshot: /screenshots/{vm_id}_{timestamp}.png
  
  Recommendation: {recommendation}
---
