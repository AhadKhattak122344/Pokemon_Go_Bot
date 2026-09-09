# Troubleshooting history

The supplied September 9 handoff reports these earlier results:

| Observation | Conclusion |
| --- | --- |
| Windows Temp permission errors; local Temp fixes test runs | Treat permissions separately from application logic |
| Container ADB tried connecting to 0.0.0.0 | Keep `adb -a -P 5037 start-server` |
| Docker/WSL had no /dev/kvm | Native Windows AVD is the local iteration path |
| API 34 su succeeded but ndk_translation hit SIGILL | Root is not the native instruction compatibility problem |
| API 36 reaches login; two accounts fail | Capture clean auth evidence before changing root |

Migration findings: the root export contains mislabeled binary/source files,
139 exact duplicate copies, two differing variants, and no active app module.
The Proxmox standalone implementation existed only in uncommitted scripts; it is
now integrated into the installed CLI. Tests were run before and after moves.
See EVIDENCE.md for this session's commands rather than older claimed results.
