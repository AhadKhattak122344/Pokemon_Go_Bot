---
name: restart-failed
description: Restart all failed instances in the fleet with automatic recovery
triggers:
  - /restart-failed
  - /recover-failed
  - /retry-failed
  - /fix-failed
actions:
  - Query all failed instances from database (SELECT * FROM instances WHERE status='failed')
  - For each failed instance:
    - Check VM status via Proxmox API
    - If VM exists but stopped: Start VM
    - If VM doesn't exist: Skip (needs redeployment)
    - Wait for boot completion
    - Re-apply device fingerprint
    - Re-apply unique identity
    - Clear Google Services data
    - Verify Play Store certification
    - Update instance status to 'running'
  - Track success/failure for each recovery attempt
  - Generate recovery report
  - Send notification via ntfy with recovery statistics
output: |
  ✅ Failed Instance Recovery Complete
  
  === Recovery Summary ===
  Total Failed: {total_failed}
  Recovered: {recovered_count} ✅
  Still Failed: {still_failed_count} ❌
  
  === Recovered Instances ===
  {recovered_table}
  | VM ID | Name | Recovery Time | Status |
  |-------|------|---------------|--------|
  {recovered_rows}
  
  === Still Failed ===
  {still_failed_table}
  | VM ID | Name | Error | Action Needed |
  |-------|------|-------|---------------|
  {still_failed_rows}
  
  Recovery Rate: {recovery_rate}%
  Total Time: {duration}s
  
  Next Steps:
  - Manually investigate still-failed instances
  - Consider redeploying unrecoverable instances: /deploy-instance --name={name}
---
