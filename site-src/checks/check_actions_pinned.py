#!/usr/bin/env python3
"""Fail on any workflow `uses:` not pinned to an exact tag or commit sha. Stdlib only."""
import re
import sys
from pathlib import Path

KEY = r"(?:^|[{,])\s*(?:-\s*)?(['\"]?)uses\1\s*:"
USES_KEY = re.compile(KEY)
USES = re.compile(KEY + r"\s*(['\"]?)([^\s'\"#,}]+)\2")
TAG = re.compile(r"^v\d+\.\d+\.\d+$")
SHA = re.compile(r"^[0-9a-f]{40}$")


def problem(ref):
    if ref.startswith("docker://"):
        return None if re.search(r"@sha256:[0-9a-f]{64}$", ref) else "docker image lacks @sha256: digest"
    if ref.startswith("./"):
        return None
    if "@" not in ref:
        return "no version pin"
    pin = ref.rsplit("@", 1)[1]
    if TAG.match(pin) or SHA.match(pin):
        return None
    return f"not pinned to an exact vX.Y.Z tag or 40-hex sha (@{pin})"


def main():
    d = Path(".github/workflows")
    files = sorted([*d.glob("*.yml"), *d.glob("*.yaml")])
    if not files:
        print(f"{d}: no workflow files found", file=sys.stderr)
        return 1
    bad = False
    for f in files:
        for n, line in enumerate(f.read_text().splitlines(), 1):
            for k in USES_KEY.finditer(line):
                m = USES.match(line, k.start())
                if not m:
                    print(f"{f}:{n}: uses value not readable on the same line; put the ref after `uses:`", file=sys.stderr)
                    bad = True
                elif msg := problem(m.group(3)):
                    print(f"{f}:{n}: {m.group(3)}: {msg}", file=sys.stderr)
                    bad = True
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
