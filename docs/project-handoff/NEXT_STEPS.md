# Next steps

1. On the existing clean API 36 AVD, capture diagnostics immediately after one
   manually reproduced sign-in failure. Examine decisive logs; do not assume
   root/integrity is the explanation. Record Android, Google packages and app version.
2. Test user-supplied owned APKs with their actual scenario package/activity.
3. Select a real Proxmox host, network/storage and Android image. Start with one
   template and one clone using docs/PROXMOX-VM-PREP.md.
4. Record Android reboot, translation, graphics, certification and actual app
   behavior independently. Prove two clones have isolated guest data before scaling.

No remaining external result is promised by code cleanup or unit tests.
