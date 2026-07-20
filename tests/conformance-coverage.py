#!/usr/bin/env python3
"""Report conformance fixture coverage."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "conformance"

def main():
    for sub in sorted(ROOT.iterdir()):
        if not sub.is_dir():
            continue
        fixtures = sorted(sub.glob("*.json"))
        print(f"{sub.name}/: {len(fixtures)} fixtures")
        for f in fixtures:
            print(f"  {f.stem}")
    print()
    total = sum(1 for _ in ROOT.rglob("*.json"))
    print(f"Total: {total} fixtures")

if __name__ == "__main__":
    main()
