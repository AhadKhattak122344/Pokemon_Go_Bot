---
name: fleet-status
description: Show comprehensive fleet status including all instances, resource usage, failed instances, and pending tasks
triggers:
  - /status
  - /fleet-status
  - /show-fleet
  - /list-instances
  - /fleet
actions:
  - Query all instances from database with status (SELECT * FROM instances ORDER BY created_at DESC)
  - Group instances by status (running, stopped, failed, deploying)
  - Query resource usage from Proxmox API for each node
    - CPU usage percentage
    - Memory usage (used/total GB)
    - Storage usage (used/total GB)
  - Identify failed instances (status='failed' or VM not responding)
  - Query pending tasks from Redis queue (LLEN task:queue)
  - Query active tasks from Redis (HGETALL instance:*:status)
  - Calculate fleet health metrics
    - Success rate: (successful deployments / total attempts) * 100
    - Average boot time
    - Uptime percentage
  - Format output as readable dashboard with tables
output: |
  📊 Pokémon GO Fleet Status Dashboard
  
  === Instance Summary ===
  Total Instances: {total}
  ├── Running: {running} ✅
  ├── Stopped: {stopped} ⏸️
  ├── Failed: {failed} ❌
  └── Deploying: {deploying} 🔄
  
  === Resource Usage ===
  Node: {node_name}
  ├── CPU: {cpu_used}/{cpu_total} cores ({cpu_percent}%)
  ├── RAM: {ram_used}GB / {ram_total}GB ({ram_percent}%)
  └── Storage: {storage_used}GB / {storage_total}GB ({storage_percent}%)
  
  === Failed Instances ===
  {failed_instances_table}
  | VM ID | Name | Error | Failed At |
  |-------|------|-------|-----------|
  {failed_rows}
  
  === Pending Tasks ===
  Queue Length: {queue_length}
  Active Tasks: {active_tasks}
  {tasks_table}
  
  === Fleet Health ===
  Deployment Success Rate: {success_rate}%
  Average Boot Time: {avg_boot_time}s
  Fleet Uptime: {uptime}%
  
  Quick Actions:
  - Restart failed: /restart-failed
  - Scale up: /scale-up --target={target}
  - Destroy all stopped: /cleanup-stopped
---
