---
name: scale-up
description: Scale the Pokémon GO fleet to a target number of instances with parallel deployment
triggers:
  - /scale
  - /scale-up
  - /deploy-fleet
  - /scale-fleet
parameters:
  - name: target
    type: integer
    required: true
    description: Target number of instances (e.g., 100)
  - name: template_id
    type: integer
    default: 9000
    description: Proxmox template ID
  - name: parallel
    type: integer
    default: 10
    description: Number of parallel deployments
actions:
  - Query current instance count from database (SELECT COUNT(*) FROM instances WHERE status='running')
  - Calculate instances needed: target - current_count
  - Check resource capacity (CPU, RAM, storage) on Proxmox nodes
  - Generate batch of unique identities (Android ID, IMEI, MAC, serial) for all new instances
  - Validate all identities for uniqueness and format compliance
  - Deploy instances in parallel batches (default: 10 at a time)
    - Clone VM from template
    - Apply unique MAC address
    - Start VM
    - Wait for boot completion
    - Apply Pixel 4 fingerprint
    - Set unique identity
    - Clear Google Services
    - Register in database
  - Monitor deployment progress and handle failures with retry logic
  - Verify all instances are healthy and Play Store certified
  - Send summary notification via ntfy with deployment statistics
output: |
  ✅ Fleet scaling complete!
  
  Target: {target} instances
  Deployed: {deployed_count} new instances
  Failed: {failed_count} instances
  Total Running: {total_running}
  
  Resource Usage:
  - CPU Cores: {cpu_used}/{cpu_total}
  - RAM: {ram_used}GB/{ram_total}GB
  - Storage: {storage_used}GB/{storage_total}GB
  
  Deployment Time: {duration_seconds}s
  Average per Instance: {avg_time}s
  
  Failed Instances: {failed_list}
  Retry Command: /retry-failed --batch={batch_id}
---
