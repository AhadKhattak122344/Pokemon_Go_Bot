# Codex Memory

This directory contains compact machine-readable and human-readable context for
future Codex sessions. It is intentionally redundant with the experiment log so a
new session can quickly avoid failed paths, then open the detailed evidence.

- `attempted_approaches.json`: searchable attempt index used by the validator.
- `current_context.md`: active state and next bounded actions.
- `decision_log.md`: rules for choosing the next recommendation or experiment.

Keep raw logs, account identifiers, screenshots, tokens, and private device data
out of this directory. Store those under ignored `artifacts/` and link only the
safe path names from tracked notes.
