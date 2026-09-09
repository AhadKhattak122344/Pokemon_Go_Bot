# Codex work harness

Project-local defaults select Terra/medium. This is Codex configuration and a
working protocol, not a Claude/DeepSeek wrapper or an account quota controller.
It applies to new sessions that load this trusted project's configuration; it
does not change the model of an already running conversation.

| Work | Model / effort | Role |
|---|---|---|
| Commands, implementation, ordinary debugging | gpt-5.6-terra / medium | lead or implementer |
| Small log extraction, documentation | gpt-5.6-luna / low | scribe |
| Difficult boot/root decision, experiment design | gpt-6-astra / medium | diagnostician |

## Start

From the repository root with Codex installed and authenticated:

```powershell
codex --strict-config --model gpt-5.6-terra -c model_reasoning_effort=medium -c agents.max_concurrent_threads_per_session=1
```

Review the model/effort and service tier in the client before starting work. This
repository does not request Fast, change global settings, or assume an account's
available tiers. Select the normal tier in your client if Fast was inherited.
No quota, pricing, caching discount, or model-access guarantee is implied.

Project config loads only for trusted projects. Named profile selection belongs
to user configuration, so this harness does not put ignored profiles in project
config. See the official [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

## Delegation contract

Use zero workers for tiny or sequential work. Delegate only meaningful independent
work while the lead has useful local work. Keep at most one worker open; close it
before another. Workers never delegate. Only the lead controls a device, VM, or
its disks. Give each worker a fresh brief using [CODEX.md](CODEX.md), with explicit
owned files, constraints, facts, acceptance checks, and report limit.

Use the named roles in `.codex/agents/`. When the collaboration API requires
explicit model/effort, pass the table's exact values with `fork_turns="none"`;
role files cannot override that API contract. Read the actual tool schema.
Local Codex supports project agent files and an open-worker cap; see official
[subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Gather logs before Astra. Supply the exact decision, observed failure, evidence
paths, attempted fixes and acceptance condition. Escalate the same bounded
decision to high only if medium reports a concrete reasoning obstacle. Record
that obstacle before changing the diagnostician's effort for that invocation;
check the effective effort because named roles pin medium. Never default to
xhigh, max or ultra. Return execution to Terra immediately after diagnosis.
In the next progress update/handoff report Astra's effort, decision and outcome.

Role sandbox defaults supplement this protocol; inherited runtime permissions
may take precedence. A read-only filesystem alone does not prevent device API
mutations. The diagnostician must inspect saved evidence only.

After failure, inspect the cause and retry only with new evidence. On unavailable
model/quota, do not repeatedly respawn or silently choose a more expensive model.
Report the limitation and checkpoint if useful progress is impossible.

## Output and checkpoints

Save full test logs locally, inspect failures with targeted searches, and preserve
the actual command exit code. Do not pipe away failures and call the run passing.
Workers return paths, exit codes and evidence in at most 200 words (300 for hard
diagnosis). Before ending a task record changed paths, verified results, remaining
uncertainties and the next bounded action in the STATE.md and experiments/EXPERIMENT_LOG.md.

## Validation

The harness adds no paid model probe. TOML parsing and Codex strict configuration
checks verify configuration locally; actual model access and future agent behavior
require a real authorized session. Run normal repository checks after code edits:

```powershell
uv run pytest -p no:cacheprovider
uv run python tools/verify_repository.py
git diff --check
```

Validation on September 9, 2026: all four TOML files parsed; Codex 0.153.4
`--strict-config` with the explicit launch flags reported config `ok` and model
`gpt-5.6-terra`. The overall doctor command exited 1 for environment diagnostics,
so this is not a fully passing doctor report. Without explicit flags the diagnostic
selected the existing Astra default: project-role loading has not been demonstrated
in a live session. Verify named-role loading before relying on it. In this collaboration runtime, explicit model/effort overrides with a fresh brief have been used successfully for Terra/medium; this does not establish local CLI role discovery.
No model call was made for this check. Repository validation: 92 tests passed,
280 archive hashes, 22 documentation files and 13 CLI help paths checked.
