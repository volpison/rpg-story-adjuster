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


def parse_mapping_str(s: str) -> dict[int, int]:
    """Parse '10:47,20:30' into {10:47, 20:30}."""
    result: dict[int, int] = {}
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            old_s, new_s = part.split(":")
            old, new = int(old_s.strip()), int(new_s.strip())
        except ValueError:
            raise ReassignError(f"invalid mapping entry: {part!r}")
        if old in result:
            raise ReassignError(f"duplicate old ID {old}")
        result[old] = new
    if not result:
        raise ReassignError("empty mapping")
    return result


# ---- In-memory (used by invariant tests) ----

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


# ---- Plan ----

@dataclass
class ReassignPlan:
    old_id: int | None          # populated for single; None for batch
    new_id: int | None          # populated for single; None for batch
    kind: str
    mapping: dict[int, int] = field(default_factory=dict)
    patches_by_file: dict[str, list[tuple]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    expected_post: dict[int, int] = field(default_factory=dict)


def _compute_expected_post(
    before_hits: dict[int, int], mapping: dict[int, int],
) -> dict[int, int]:
    """Compute {id: expected_hits_after_apply}.

    After apply, hit X moves to mapping.get(X, X). So expected_post[Z] is the
    sum of before_hits[X] for every X whose resulting ID is Z. All sources are
    included in the result so a "should be 0" check works uniformly.
    """
    result: dict[int, int] = {}
    for x, cnt in before_hits.items():
        dest = mapping.get(x, x)
        result[dest] = result.get(dest, 0) + cnt
    for src in mapping.keys():
        if src not in result:
            result[src] = 0
    return result


def build_batch_plan(
    root: Path, kind: str, mapping: dict[int, int],
) -> ReassignPlan:
    """Build a batch reassign plan. Handles single-pair dicts identically."""
    if not mapping:
        raise ReassignError("empty mapping")

    for old, new in mapping.items():
        if old < 1 or new < 1:
            raise ReassignError("IDs must be positive")
        if old == new:
            raise ReassignError(f"old_id == new_id for {old}")

    targets = list(mapping.values())
    if len(set(targets)) != len(targets):
        seen: set[int] = set()
        dups = [t for t in targets if t in seen or seen.add(t)]  # type: ignore[func-returns-value]
        raise ReassignError(f"duplicate target ID(s): {sorted(set(dups))}")

    sources = set(mapping.keys())
    all_ids = sources | set(targets)

    scan_results = {id_: scan_project(root, kind, id_) for id_ in all_ids}
    before_hits = {id_: len(scan_results[id_].hits) for id_ in all_ids}

    for new in targets:
        if new not in sources and before_hits.get(new, 0) > 0:
            raise ReassignError(
                f"refusing: {kind} {new} is already in use "
                f"({before_hits[new]} hit(s))"
            )

    plan = ReassignPlan(old_id=None, new_id=None, kind=kind, mapping=dict(mapping))

    for old, new in mapping.items():
        result = scan_results[old]
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
            base = hit.source.json_path + ("parameters",)
            for pi in hit.param_indices:
                plan.patches_by_file.setdefault(hit.source.file, []).append(
                    (base + (pi,), old, new)
                )
        for d in result.dynamic:
            plan.warnings.append(
                f"dynamic {d.via}: {d.source.file} "
                f"ev={d.source.event_id} pg={d.source.page_index} "
                f"idx={d.source.command_index} ({d.snippet})"
            )

    plan.expected_post = _compute_expected_post(before_hits, mapping)
    return plan


def build_plan(root: Path, kind: str, old_id: int, new_id: int) -> ReassignPlan:
    """Single-pair wrapper around build_batch_plan."""
    plan = build_batch_plan(root, kind, {old_id: new_id})
    plan.old_id = old_id
    plan.new_id = new_id
    return plan


# ---- Apply ----

def _make_backup_dir(root: Path) -> Path:
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
    """Write patches, rescan to verify the invariant, roll back on any failure.

    Backups go to `<project>/.rpgadj_backups/<timestamp>/` before any write.
    Returns the backup directory on success (None if write_backups=False).
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

    hint = (
        f"Original files preserved at: {backup_dir}"
        if backup_dir else "No on-disk backup; only in-memory rollback available."
    )
    # Generalized post-check: every ID in expected_post must match.
    for id_, expected in plan.expected_post.items():
        after = scan_project(root, plan.kind, id_)
        if len(after.hits) != expected:
            raise ReassignError(
                f"post-check failed for {plan.kind} {id_}: "
                f"expected {expected} hit(s), got {len(after.hits)}. "
                f"Files written: {written}. {hint}"
            )
    return backup_dir