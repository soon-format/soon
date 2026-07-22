"""GCF encoder wrapper — calls the @blackwell-systems/gcf npm package via Node.

Requires Node.js and the playground's node_modules to be installed
(``cd playground && npm install``).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

_PLAYGROUND = Path(__file__).resolve().parents[2] / "playground"
_NODE_MODULES = _PLAYGROUND / "node_modules" / "@blackwell-systems" / "gcf"

_SCRIPT = """\
const {encodeGeneric} = require('@blackwell-systems/gcf');
const data = JSON.parse(process.argv[1]);
process.stdout.write(encodeGeneric(data));
"""


def encode(value: Any) -> str:
    if not _NODE_MODULES.exists():
        raise RuntimeError(
            "GCF npm package not found. Run: cd playground && npm install"
        )
    payload = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    result = subprocess.run(
        ["node", "-e", _SCRIPT, payload],
        cwd=str(_PLAYGROUND),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"GCF encode failed: {result.stderr.strip()}")
    return result.stdout
