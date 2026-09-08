---
name: set-location
description: Set GPS location for a Pokémon GO instance with coordinates and optional route
triggers:
  - /set-location
  - /set-loc
  - /teleport
  - /gps-set
  - /location
parameters:
  - name: vm_id
    type: integer
    required: true
    description: Proxmox VM ID (e.g., 10001)
  - name: latitude
    type: number
    required: true
    description: GPS latitude coordinate (e.g., 40.7128)
  - name: longitude
    type: number
    required: true
    description: GPS longitude coordinate (e.g., -74.0060)
  - name: altitude
    type: number
    required: false
    default: 10
    description: Altitude in meters
  - name: route_file
    type: string
    required: false
    description: Path to GPX/KML route file for movement simulation
actions:
  - Validate VM exists and is running
  - Get VM IP address and connect via ADB
  - Verify Pokémon GO is installed
  - If route_file provided:
    - Parse GPX/KML file
    - Validate route coordinates
    - Simulate movement along route at walking speed
  - Else (single location):
    - Use ADB to set mock location via broadcast intent:
      adb shell am broadcast -a com.android.gps.mock \
        --es lat {latitude} --es lon {longitude} --es alt {altitude}
    - Or use LSPosed GPS spoofing module:
      adb shell su -c "settings put secure mock_location {latitude},{longitude}"
  - Verify location is set correctly:
    - Query current location from device
    - Compare with target coordinates
  - Send location notification via ntfy
output: |
  ✅ Location set successfully!
  
  VM ID: {vm_id}
  Name: {vm_name}
  
  Target Location:
  ├── Latitude: {latitude}
  ├── Longitude: {longitude}
  └── Altitude: {altitude}m
  
  Location Name: {location_name}
  Distance from Previous: {distance}km
  
  Method: {method}
  Status: ACTIVE ✅
  
  ⚠️ Remember: Use realistic movement speeds to avoid detection!
---
