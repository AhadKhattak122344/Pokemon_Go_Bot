---
name: destroy-instance
description: Destroy a VM instance, remove from database, and cleanup storage
triggers:
  - /destroy
  - /destroy-instance
  - /remove-vm
  - /remove-instance
  - /delete-instance
parameters:
  - name: vm_id
    type: integer
    required: true
    description: Proxmox VM ID to destroy (e.g., 10001)
  - name: force
    type: boolean
    default: false
    description: Force destruction even if VM is running
actions:
  - Query instance from database to verify existence
  - Check VM status via Proxmox API (GET /nodes/{node}/qemu/{vmid}/status/current)
  - If VM is running and force=false, stop VM gracefully (POST /status/stop)
  - If VM is running and force=true, send power-off command
  - Wait for VM to fully stop (poll status until stopped)
  - Destroy VM via Proxmox API (DELETE /nodes/{node}/qemu/{vmid})
  - Remove instance record from database (DELETE FROM instances WHERE vm_id={vm_id})
  - Remove identity profile from database (DELETE FROM identity_profiles WHERE instance_id={instance_id})
  - Cleanup associated storage volumes if not automatically removed
  - Send destruction notification via ntfy
output: |
  ✅ Instance destroyed successfully!
  
  VM ID: {vm_id}
  Name: {vm_name}
  Status: DESTROYED
  
  Database Records Removed:
  - Instance: {instance_id}
  - Identity Profile: {identity_profile_id}
  
  Storage Freed: {disk_size}GB
  
  Remaining Instances: {remaining_count}
---
