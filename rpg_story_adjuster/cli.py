from __future__ import annotations
import argparse
import sys
from pathlib import Path


def _add_reassign_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("project_root", type=Path)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--switch", type=int, metavar="OLD_ID")
    g.add_argument("--variable", type=int, metavar="OLD_ID")
    p.add_argument("--to", type=int, required=True, metavar="NEW_ID")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rpg-story-adjuster")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("gui", help="Open the GUI (default when no subcommand given).")

    lf = sub.add_parser("list-files", help="List *.json under <project>/data/.")
    lf.add_argument("project_root", type=Path)

    lc = sub.add_parser("list-commands",
                        help="Walk every command list; print file/event/page/index.")
    lc.add_argument("project_root", type=Path)
    lc.add_argument("--file", default=None)
    lc.add_argument("--limit", type=int, default=0)

    sc = sub.add_parser("scan", help="Scan a project for a switch/variable ID.")
    sc.add_argument("project_root", type=Path)
    g = sc.add_mutually_exclusive_group(required=True)
    g.add_argument("--switch", type=int, metavar="ID")
    g.add_argument("--variable", type=int, metavar="ID")
    sc.add_argument("--show-dynamic", action="store_true")

    dr = sub.add_parser("reassign-dry-run",
                        help="Preview a switch/variable ID reassign.")
    _add_reassign_args(dr)

    ap = sub.add_parser("reassign-apply",
                        help="Apply a switch/variable ID reassign (writes files).")
    _add_reassign_args(ap)

    return p


def main(argv: list[str] | None = None) -> int:
    # Windows redirects default to cp1252 which chokes on emoji and other
    # non-cp1252 characters in text parameters. Force UTF-8 on both streams;
    # replace (not raise) on unencodable characters so we degrade gracefully
    # instead of silently truncating output mid-file.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    args = build_parser().parse_args(argv)

    if args.command in (None, "gui"):
        from rpg_story_adjuster.gui.main_window import run
        return run()

    if args.command == "list-files":
        from rpg_story_adjuster.project import Project
        proj = Project(args.project_root)
        for f in proj.list_data_files():
            print(f.relative_to(proj.root))
        return 0

    if args.command == "list-commands":
        from rpg_story_adjuster.walker import iter_project_commands
        n = 0
        try:
            for cmd in iter_project_commands(args.project_root):
                if args.file and not cmd.source.file.endswith(args.file):
                    continue
                loc = cmd.source
                print(
                    f"{loc.file} | ev={loc.event_id} pg={loc.page_index} "
                    f"idx={loc.command_index} | "
                    f"code={cmd.code} indent={cmd.indent} "
                    f"params={cmd.parameters!r}"
                )
                n += 1
                if args.limit and n >= args.limit:
                    break
        except FileNotFoundError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"\n-- {n} command(s)", file=sys.stderr)
        return 0

    if args.command == "scan":
        from rpg_story_adjuster.scan import scan_project
        kind = "switch" if args.switch is not None else "variable"
        qid = args.switch if args.switch is not None else args.variable
        result = scan_project(args.project_root, kind, qid)
        print(f"{kind} {qid} - {len(result.hits)} hit(s)")
        for h in result.hits:
            s = h.source
            extra = f" | {h.detail}" if h.detail else ""
            print(f"  {s.file} | ev={s.event_id} pg={s.page_index} "
                  f"idx={s.command_index} | via={h.via} | "
                  f"params{h.param_indices}{extra}")
        if args.show_dynamic and result.dynamic:
            print(f"\nDYNAMIC - {len(result.dynamic)}")
            for d in result.dynamic:
                s = d.source
                print(f"  {s.file} | ev={s.event_id} pg={s.page_index} "
                      f"idx={s.command_index} | via={d.via} | {d.snippet}")
        return 0

    if args.command in ("reassign-dry-run", "reassign-apply"):
        from rpg_story_adjuster.apply import (
            build_plan, apply_plan, ReassignError,
        )
        kind = "switch" if args.switch is not None else "variable"
        old_id = args.switch if args.switch is not None else args.variable
        new_id = args.to
        try:
            plan = build_plan(args.project_root, kind, old_id, new_id)
        except ReassignError as e:
            print(f"refused: {e}", file=sys.stderr)
            return 1
        total = sum(len(v) for v in plan.patches_by_file.values())
        print(f"{kind} {old_id} -> {new_id}: {total} patch(es) "
              f"across {len(plan.patches_by_file)} file(s)")
        for f, patches in sorted(plan.patches_by_file.items()):
            for path, o, n in patches:
                print(f"  {f} :: {path} :: {o} -> {n}")
        for w in plan.warnings:
            print(f"  WARN {w}")
        if args.command == "reassign-dry-run":
            print("\ndry run - nothing written")
            return 0
        try:
            backup_dir = apply_plan(args.project_root, plan)
        except Exception as e:
            print(f"apply failed: {e}", file=sys.stderr)
            return 1
        print(f"\napplied. post-scan invariant verified.")
        if backup_dir:
            print(f"backup: {backup_dir}")
        return 0

    return 2