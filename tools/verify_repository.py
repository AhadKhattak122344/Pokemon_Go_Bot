"""Check archive preservation, active documentation links and CLI registration."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors = []
    mapping = json.loads((ROOT / 'archive/recovered/migration-map.json').read_text())
    for item in mapping:
        path = ROOT / item['destination']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            errors.append(f"Archive bytes changed: {item['source']}")
    docs = [ROOT / name for name in ('README.md', 'START-HERE.md', 'AGENTS.md', 'QWEN.md')]
    docs += [ROOT / 'docs' / name for name in (
        'ARCHITECTURE.md', 'CODEX.md', 'COMMANDS.md', 'DEBUGGING.md',
        'INSTALLED_COMPONENTS.md', 'MODEL_STRATEGY.md', 'STATE.md',
    )]
    docs += list((ROOT / 'experiments').rglob('*.md')) if (ROOT / 'experiments').is_dir() else []
    for doc in docs:
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', doc.read_text(encoding='utf-8')):
            if '://' in link or link.startswith('#'):
                continue
            target = unquote(link.split('#')[0])
            if not (doc.parent / target).exists():
                errors.append(f"Broken link in {doc.relative_to(ROOT)}: {link}")
    commands = [[], ['proxmox'], ['diagnostics'], ['connect'], ['up'], ['down'],
                ['status'], ['smoke'], ['install'], ['root'], ['location'],
                ['location', 'set'], ['location', 'follow']]
    for command in commands:
        result = subprocess.run([sys.executable, '-m', 'android_lab.cli', *command, '--help'],
                                capture_output=True, text=True, timeout=30, cwd=ROOT)
        if result.returncode:
            errors.append(f"CLI parser failed for {command}: {result.stderr}")
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'PASS: {len(mapping)} archive hashes, {len(docs)} documentation files, {len(commands)} CLI help paths')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
