# Decision Log

Last updated: 2026-09-14

## When API 34 Is Mentioned

Check F01. Do not recommend API 34 for Pokemon GO login or root hiding. The
known failure is native translation SIGILL.

## When API 36 Is Mentioned

Use API 36 as the verified local process-launch baseline. Do not call it a login
or certification success. Repeating the same designated-account login is blocked
unless a new variable or new evidence exists.

## When API 36.1 Is Mentioned

Check L19-L21. Boot markers were misleading because display capture failed after
SurfaceFlinger assertions. Do not retry the same auto/software/shared-slot matrix.

## When API 37 Is Mentioned

Check L22. Auto/host rendering timed out with ADB offline. The next recorded
single-variable comparison is software GPU mode, not another auto/host run.

## When Proxmox Is Mentioned

Start with `lab proxmox plan`. Treat plan/preflight/deploy success as VM lifecycle
evidence only. Android readiness, Play certification, app launch, login, and
two-clone isolation require separate guest acceptance.

## Before Suggesting Any Fix

1. Run `tools/validate_against_history.py` on the proposed change.
2. If it matches a non-retryable failure, use the documented alternative.
3. If it is new, create or append a bounded experiment entry with one changed
   variable and artifact paths.
