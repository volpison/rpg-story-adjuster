"""Dump raw bytes of a small data file to inspect its exact format.

Run: python tools/dump_head.py <file> [bytes=1500]
"""
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: dump_head.py <file> [bytes=1500]", file=sys.stderr)
        return 2

    p = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    raw_full = p.read_bytes()
    raw = raw_full[:n]

    print(f"file: {p}  size: {len(raw_full)} bytes")
    print(f"--- first {len(raw)} bytes as repr ---")
    print(repr(raw))
    print()

    nl_positions = [i for i, b in enumerate(raw) if b == 0x0A]
    print(f"--- LF byte offsets within first {len(raw)} bytes ---")
    print(nl_positions)
    print()
    for i in nl_positions:
        before = raw[max(0, i - 20):i]
        after = raw[i + 1:i + 21]
        print(f"  LF@{i:5d}  ...{before!r} <LF> {after!r}...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())