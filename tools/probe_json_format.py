"""Probe RPG Maker MZ data/*.json formatting.

Run: python tools/probe_json_format.py <project-root>

Reports per file: size, line count, line ending, BOM, indentation style,
whether json.dumps reproduces the file byte-for-byte under any common style,
key ordering (sorted vs insertion), and object counts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CANDIDATES = [
    ("minified",       dict(separators=(",", ":"),  ensure_ascii=False)),
    ("minified_ascii", dict(separators=(",", ":"),  ensure_ascii=True)),
    ("default",        dict(separators=(", ", ": "), ensure_ascii=False)),
    ("indent2",        dict(indent=2, separators=(",", ": "), ensure_ascii=False)),
    ("indent2_full",   dict(indent=2, ensure_ascii=False)),
    ("indent4",        dict(indent=4, separators=(",", ": "), ensure_ascii=False)),
]


def probe_one(path: Path) -> dict:
    raw = path.read_bytes()
    r: dict = {"path": str(path), "size": len(raw),
               "bom": raw.startswith(b"\xef\xbb\xbf")}
    body = raw[3:] if r["bom"] else raw

    if b"\r\n" in body:
        r["line_end"] = "CRLF"
    elif b"\n" in body:
        r["line_end"] = "LF"
    else:
        r["line_end"] = "none"
    r["lines"] = body.count(b"\n") + (0 if body.endswith(b"\n") else 1)
    r["trailing_newline"] = body.endswith(b"\n")

    # Detect indentation from the first indented line.
    indent = None
    for ln in body.split(b"\n")[1:]:
        if ln.startswith(b"\t"):
            indent = ("tab", 1); break
        stripped = ln.lstrip(b" ")
        if stripped != ln:
            indent = ("space", len(ln) - len(stripped)); break
    r["indent"] = indent

    data = json.loads(body.decode("utf-8"))

    matches = []
    for name, kw in CANDIDATES:
        try:
            if json.dumps(data, **kw).encode("utf-8") == body:
                matches.append(name)
        except Exception:
            continue
    r["canonical_matches"] = matches

    total = sorted_n = 0
    def walk(o):
        nonlocal total, sorted_n
        if isinstance(o, dict):
            total += 1
            if list(o.keys()) == sorted(o.keys()):
                sorted_n += 1
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(data)
    r["objects"], r["sorted_objects"] = total, sorted_n
    return r


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: probe_json_format.py <project-root>", file=sys.stderr)
        return 2
    data_dir = Path(sys.argv[1]) / "data"
    if not data_dir.is_dir():
        print(f"no data/ under {sys.argv[1]}", file=sys.stderr)
        return 2
    files = sorted(data_dir.glob("*.json"))
    if not files:
        print(f"no *.json under {data_dir}", file=sys.stderr)
        return 2
    for f in files:
        try:
            s = probe_one(f)
        except Exception as e:
            print(f"ERROR {f}: {e}", file=sys.stderr); continue
        print(f"\n{s['path']}")
        print(f"  size={s['size']}  lines={s['lines']}  line_end={s['line_end']}"
              f"  bom={s['bom']}  trailing_nl={s['trailing_newline']}")
        print(f"  indent={s['indent']}")
        print(f"  canonical_matches={s['canonical_matches'] or 'NONE'}")
        print(f"  objects={s['objects']}  sorted={s['sorted_objects']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
