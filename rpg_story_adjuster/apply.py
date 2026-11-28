from __future__ import annotations
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from rpg_story_adjuster.model import Command
from rpg_story_adjuster.commands import table
from rpg_story_adjuster.jsonio_surgical import patch_numbers_in_file
from rpg_story_adjuster.scan import scan_project


class ReassignError(Exception):
    pass


# ---- In-memory (used by invariant tests, Phase 1) ----

@dataclass
class ApplyResult:
    rewritten: int = 0
    skipped_ranges: int = 0
    skipped_script: int = 0


def apply_reassign_to_commands(
    commands: Iterable[Command], kind: str, old_id: int, new_id: int,
) -> ApplyResult:
    r = ApplyResult()
    for cmd in commands:
        spec = table.get(cmd.code)
        if spec is None:
            continue
        roles = spec.roles(cmd.parameters)
        end_role = next((x for x in roles if x.kind == f"{kind}_range_end"), None)
        for role in roles:
            if role.kind == f"{kind}_range_start" and end_role is not None:
                try:
                    start = cmd.parameters[role.index]
                    end = cmd.parameters[end_role.index]
                except IndexError:
                    continue
                if not (isinstance(start, int) and isinstance(end, int)):
                    continue
                if start == end == old_id:
                    cmd.parameters[role.index] = new_id
                    cmd.parameters[end_role.index] = new_id
                    r.rewritten += 1
                elif min(start, end) <= old_id <= max(start, end):
                    r.skipped_ranges += 1
            elif role.kind == kind:
                try:
                    if cmd.parameters[role.index] == old_id:
                        cmd.parameters[role.index] = new_id
                        r.rewritten += 1
                except IndexError:
                    continue
            elif role.kind in ("script", "text"):
                try:
                    v = cmd.parameters[role.index]
                except IndexError:
                    continue
                if isinstance(v, str) and str(old_id) in v:
                    r.skipped_script += 1
    return r


# ---- On-disk (Phase 4-lite) ----

@dataclass
class ReassignPlan:
    old_id: int
    new_id: int
    kind: str
    patches_by_file: dict[str, list[tuple]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    expected_new_hits: int = 0


def build_plan(root: Path, kind: str, old_id: int, new_id: int) -> ReassignPlan:
    """Scan, validate, and prepare a reassign plan. Does not write."""
    if old_id == new_id:
        raise ReassignError("old_id == new_id; nothing to do")
    if old_id < 1 or new_id < 1:
        raise ReassignError("IDs must be positive")

    existing_new = scan_project(root, kind, new_id)
    if existing_new.hits:
        raise ReassignError(
            f"refusing: {kind} {new_id} is already in use "
            f"({len(existing_new.hits)} hit(s))"
        )

    result = scan_project(root, kind, old_id)
    plan = ReassignPlan(old_id=old_id, new_id=new_id, kind=kind)

    for hit in result.hits:
        if hit.via == "range":
            plan.warnings.append(
                f"skip range {hit.range_bounds}: {hit.source.file} "
                f"ev={hit.source.event_id} pg={hit.source.page_index} "
                f"idx={hit.source.command_index}"
            )
            continue
        if hit.via in ("script", "text"):
            plan.warnings.append(
                f"skip {hit.via}: {hit.source.file} "
                f"ev={hit.source.event_id} pg={hit.source.page_index} "
                f"idx={hit.source.command_index} ({hit.detail})"
            )
            continue
        # via == "command" -- one hit, regardless of how many slots it touches.
        plan.expected_new_hits += 1
        base = hit.source.json_path + ("parameters",)
        for pi in hit.param_indices:
            plan.patches_by_file.setdefault(hit.source.file, []).append(
                (base + (pi,), old_id, new_id)
            )

    for d in result.dynamic:
        plan.warnings.append(
            f"dynamic {d.via}: {d.source.file} "
            f"ev={d.source.event_id} pg={d.source.page_index} "
            f"idx={d.source.command_index} ({d.snippet})"
        )

    return plan


def _make_backup_dir(root: Path) -> Path:
    """Create a fresh timestamped backup folder under <project>/.rpgadj_backups/.

    One folder per apply operation. Never reused, never overwritten.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = root / ".rpgadj_backups" / stamp
    n = 0
    while base.exists():
        n += 1
        base = root / ".rpgadj_backups" / f"{stamp}-{n}"
    base.mkdir(parents=True)
    return base


def apply_plan(
    root: Path, plan: ReassignPlan, *, write_backups: bool = True,
) -> Path | None:
    """Write every patch atomically per file. Roll back on any failure.

    Before any byte is written, copies every file that will be touched into
    `<project>/.rpgadj_backups/<timestamp>/`. Returns that directory on success
    so the caller can print it; the folder is deliberately left in place.

    If `write_backups=False` (tests), no backup folder is created and rollback
    relies on the in-memory snapshot only.
    """
    if not plan.patches_by_file:
        return None

    backups: dict[Path, bytes] = {}
    written: list[Path] = []
    backup_dir: Path | None = None

    if write_backups:
        backup_dir = _make_backup_dir(root)
        for rel_file in plan.patches_by_file:
            full = root / rel_file
            dest = backup_dir / rel_file
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, dest)

    try:
        for rel_file, patches in plan.patches_by_file.items():
            full = root / rel_file
            backups[full] = full.read_bytes()
            patch_numbers_in_file(full, patches)
            written.append(full)
    except Exception:
        for p, raw in backups.items():
            try:
                p.write_bytes(raw)
            except Exception:
                pass
        raise

    after_old = scan_project(root, plan.kind, plan.old_id)
    after_new = scan_project(root, plan.kind, plan.new_id)
    hint = (
        f"Original files preserved at: {backup_dir}"
        if backup_dir else "No on-disk backup; only in-memory rollback available."
    )
    if after_old.hits:
        raise ReassignError(
            f"post-check failed: {plan.kind} {plan.old_id} still has "
            f"{len(after_old.hits)} hit(s). Files written: {written}. {hint}"
        )
    if len(after_new.hits) != plan.expected_new_hits:
        raise ReassignError(
            f"post-check failed: expected {plan.expected_new_hits} hit(s) "
            f"for {plan.kind} {plan.new_id}, got {len(after_new.hits)}. {hint}"
        )
    return backup_dir