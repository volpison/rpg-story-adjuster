# Roadmap — RPG Story Adjuster

Phased plan. Each phase should leave the project in a usable, testable state.  
**No write path is enabled until the corresponding dry-run / round-trip checks pass.**

---

## Guiding principles

1. **Round-trip first** — Readable form → JSON must produce engine-acceptable data. Prefer failing loudly over silent corruption.
2. **Dry-run by default** — Scans and previews never modify the project until the user explicitly confirms.
3. **Literal IDs only (for reassign)** — Dynamic references (`$gameSwitches.value(x)` where `x` is not a number) are reported, never rewritten automatically.
4. **Sibling, not fork** — Asset-level work stays in [rpg-asset-tools](https://github.com/volpison/rpg-asset-tools). This repo owns event *logic* and representations of it.
5. **Small vertical slices** — Prefer a thin end-to-end path (one command family, one map) over a wide half-finished surface.

---

## Phase 0 — Foundation

**Goal:** Repo layout, shared types, and a single well-tested path for reading command lists.

- [ ] Project skeleton (`src/` or package layout, tests, `pyproject` / requirements)
- [ ] Load `data/Map*.json`, `CommonEvents.json`, `Troops.json` safely
- [ ] Shared model for a command: `code`, `indent`, `parameters`, source location
- [ ] Table of known MZ command codes (at least the ones we will pretty-print first)
- [ ] Unit tests on synthetic minimal maps / common events

**Exit criteria:** Can load a project and list every command with file / event / page / index without crashing on malformed entries.

---

## Phase 1 — Cryptic → readable (one way)

**Goal:** Pretty-print event commands into a stable, line-oriented text form.

Example direction (exact syntax TBD):

```text
# Map001.json · event 3 · page 1
◆ Control Variables: Variable[100] -= 308
◆ Conditional Branch: Switch[10] is ON
  ◆ Text: Hello
  ◆
◆
```

Planned work:

- [ ] Pretty-printer for a priority set of codes:
  - Control Switches (121)
  - Control Variables (122)
  - Conditional Branch (111) — switch / variable / else branches
  - Show Text / Show Choices (and continuations)
  - Comment, Label, Jump to Label
  - Common Event call
  - Script (355 / 655) as raw blocks
- [ ] Stable indentation rules matching MZ `indent`
- [ ] Unknown codes printed as safe fallback (`Code 999: [raw parameters]`)
- [ ] CLI or library entry: `map → text` for one file or whole `data/`

**Exit criteria:** Pretty-print of a real project’s maps is readable and deterministic (same input → same text).

---

## Phase 2 — Readable → cryptic (round-trip)

**Goal:** Parse the text form back into MZ command JSON that the editor and engine accept.

- [ ] Parser for the Phase 1 syntax
- [ ] Emit `code` / `indent` / `parameters` with the same shapes MZ uses
- [ ] Round-trip tests: JSON → text → JSON equality (or semantic equality where parameter order is fixed)
- [ ] Reject ambiguous or partial lines instead of guessing
- [ ] Document intentional limitations (plugin commands, exotic parameter packs)

**Exit criteria:** A map can go JSON → text → JSON and still open in RPG Maker MZ with behavior unchanged for the supported command set.

---

## Phase 3 — Switch / variable ID reassign

**Goal:** Bulk change of numeric IDs used by events (not merely labels in `System.json`).

Example need: every `Set Switch 10` and every `If Switch 10` becomes ID 47.

### 3a — Scanner + dry-run (no writes)

- [ ] Find literal usages in:
  - Control Switches / Control Variables
  - Conditional Branch (switch / variable)
  - Page conditions (maps, troops, common events)
  - Script literals (`$gameSwitches.value(10)`, `.setValue(10, …)`, variable equivalents)
  - Text codes `\V[n]`
- [ ] Report: file, event, page, command index, role (set / read / condition / script / text)
- [ ] Flag dynamic references as warnings only

### 3b — Apply path (after 3a is trusted)

- [ ] Preview UI or CLI confirmation listing every hit
- [ ] Backups under a project-local folder before any write
- [ ] Per-file apply with rollback on failure
- [ ] Signature check: refuse if files changed since scan
- [ ] Optional: update labels in `System.json` (off by default)

**Exit criteria:** Dry-run on a large project is reviewable; apply + undo on a disposable copy leaves the project loadable and logic consistent for the remapped ID.

---

## Phase 4 — Dialogue / text → events (exploratory)

**Goal:** Help turn structured dialogue or simple scripts into event command lists.

Inspiration (prior art, not a dependency):

- Text-to-frame style tools that expand dialogue into Show Text / choices / waits

Planned exploration:

- [ ] Minimal input format (e.g. markdown-like or YAML scenes)
- [ ] Emit Show Text, face/name boxes, simple choices, waits
- [ ] Insert generated lists into a target event page (or produce a standalone snippet)
- [ ] Keep scope small: no full quest graph, no battle logic in v1

**Exit criteria:** A short sample scene file produces a command list that round-trips through Phase 2 and plays correctly in-engine.

---

## Phase 5 — Polish & integration

- [ ] Unified CLI (`print`, `parse`, `reassign-dry-run`, `reassign-apply`)
- [ ] Optional thin GUI later (not required for usefulness)
- [ ] Cross-links / optional interop notes with rpg-asset-tools (e.g. “open this map’s assets”)
- [ ] Packaging and versioned releases

---

## Brainstorm — ideas worth considering later

These are **not** commitments. Capture only.

| Idea | Notes |
|------|--------|
| Diff two versions of a map in readable form | Easier code-review of story changes |
| “Where is switch N used?” report | Overlaps Phase 3a; could be a standalone query |
| Batch reassign from a CSV (old_id → new_id) | Power-user workflow after single-ID path works |
| Plugin command registry | Optional YAML/JSON describing `@command` shapes for prettier plugin lines |
| Preserve unknown / future codes byte-for-byte | Critical for not destroying plugin data |
| Read-only “story lint” | Unreachable pages, empty branches, switches set but never read |
| Export a single event as a snippet for sharing | Without shipping the whole map |

---

## Explicitly deferred / out of scope for now

- Editing `System.json` switch/variable *names* as a primary feature (labels only; optional side effect of reassign)
- Rewriting compiled plugin JS
- Save-file migration when IDs change (document the limitation instead)
- MV-only projects (MZ first; MV may share a lot but is not the initial target)

---

## Success metrics (project level)

1. A developer can pretty-print and round-trip a non-trivial map without opening RPG Maker.
2. Switch/variable reassign has a dry-run that a careful user trusts enough to apply on a copy.
3. Failures are visible (parse errors, unsupported codes, dynamic refs) rather than silent.
4. The tool never claims to support more command shapes than the tests cover.

---

*Last updated: initial draft. Adjust phases as implementation teaches us what is hard.*
