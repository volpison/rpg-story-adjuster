# Roadmap — RPG Story Adjuster

Phased plan. Each phase should leave the project in a usable, testable state.  
**No write path is enabled until the corresponding dry-run / round-trip checks pass.**

---

## Guiding principles

1. **Round-trip first** — Readable form → JSON must produce engine-acceptable data. Prefer failing loudly over silent corruption.
2. **Dry-run by default** — Scans and previews never modify the project until the user explicitly confirms.
3. **Literal IDs only (for reassign)** — Dynamic references (`$gameSwitches.value(x)` where `x` is not a number) are reported, never rewritten automatically.
4. **Sibling, not fork** — Asset-level work stays in [rpg-asset-tools](https://github.com/volpison/rpg-asset-tools). This repo owns event *logic* and representations of it. (Asset Tools’ roadmap points here for ID reassign.)
5. **Small vertical slices** — Prefer a thin end-to-end path (one command family, one map) over a wide half-finished surface.
6. **One command table is the source of truth** — Every command code with the role of each parameter. The printer, the parser and the ID scan all read it; nothing else knows where an ID can hide.
7. **Lossless by construction** — A command we do not know is kept as a raw JSON node, byte-for-byte. Indent levels and the closing `code 0` entries survive.
8. **Only what is edited changes** — Untouched files and events stay byte-identical (patch mode). Reuse a byte-exact JSON writer so a one-ID change is a one-line Git diff.
9. **Prove it by scanning again** — After any apply, rescan: the old ID must have no hits, and the new ID must have exactly its old hits plus the moved ones.
10. **House rules from the first commit** — Work on a branch, one topic per pull request with a "Check before merging" list, a decisions log, versioned data formats, tests run before pushing, and honest notes about what was and was not verified.

---

## Phase 0 — Foundation

**Goal:** Repo layout, shared types, and a single well-tested path for reading command lists.

- [ ] Project skeleton (`src/` or package layout, tests, `pyproject` / requirements); command line first, no GUI in the core
- [ ] Load `data/Map*.json`, `CommonEvents.json`, `Troops.json` safely
- [ ] Shared model for a command: `code`, `indent`, `parameters`, source location (file, event, page, index)
- [ ] **Command table** of MZ command codes with the role of every parameter (switch ID, variable ID, operand type, text, script, …), starting with the codes we pretty-print first and every code that can hold a switch or variable ID
- [ ] Byte-exact JSON read/write (MZ’s compact layout), so unchanged files can be written back identically
- [ ] Unit tests on synthetic minimal maps / common events; a small set of fixtures per command family
- [ ] Decisions log and data-format notes (versioned from the start)

**Exit criteria:** Can load a project and list every command with file / event / page / index without crashing on malformed entries, and write an unchanged file back byte-for-byte.

---

## Phase 1 — Where is it used? (read-only scan)

**Goal:** The scanner for switch / variable IDs, built on the command table. It is useful on its own ("where is switch 10 used?") and it is the base of reassign.

- [ ] Find literal usages in:
  - Control Switches / Control Variables (including a variable used as the **operand** of Control Variables)
  - Conditional Branch (switch; variable, including a variable **compared with another variable**; script branch)
  - Every other command that takes a variable ID (Input Number, Select Item, Change Gold / Items / Weapons / Armors, Transfer Player and Set Event Location by variable, pictures, Get Location Info, …) — the table decides, not guesswork
  - Page conditions (maps, troops, common events), enemy action conditions, common event auto-run switches
  - Script literals (`$gameSwitches.value(10)`, `.setValue(10, …)`, variable equivalents), in every place a script can sit (script commands, branch scripts, Control Variables script operand, move-route scripts)
  - Text codes `\V[n]`, also in database text
- [ ] A number that is only part of an expression (`$gameSwitches.value(10+1)`) is **not** a hit for 10; it is reported as dynamic
- [ ] A Control Switches / Variables **range** that contains the ID is reported as such (it cannot be rewritten by changing one number)
- [ ] Report: file, event, page, command index, parameter slot, role (set / read / condition / script / text)
- [ ] Flag dynamic references as warnings only
- [ ] Tests for every case above, one fixture each

**Exit criteria:** On a large real project (a copy) the report is reviewable, has no crashes, and every case in the list has a passing test.

---

## Phase 2 — Cryptic → readable (one way)

**Goal:** Pretty-print event commands into a stable, line-oriented text form.

Example direction (exact syntax TBD):

```text
# Map001.json · event 3 · page 1
◆ Control Variables: Variable[308] -= 100
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
- [ ] Unknown codes printed as a safe raw fallback that the parser can read back exactly (e.g. `Code 999: [raw parameters]`)
- [ ] Commands that belong together stay together (text lines, script lines, choices with their branches, move routes)
- [ ] CLI or library entry: `map → text` for one file or whole `data/`

**Exit criteria:** Pretty-print of a real project’s maps is readable and deterministic (same input → same text).

---

## Phase 3 — Readable → cryptic (round-trip)

**Goal:** Parse the text form back into MZ command JSON that the editor and engine accept.

- [ ] Parser for the Phase 2 syntax
- [ ] Emit `code` / `indent` / `parameters` with the same shapes MZ uses
- [ ] Round-trip tests: JSON → text → JSON equality, and **byte-identical files** when nothing was edited
- [ ] Patch mode: only events whose text changed are rewritten; everything else is left byte-for-byte
- [ ] Reject ambiguous or partial lines instead of guessing
- [ ] Document intentional limitations (plugin commands, exotic parameter packs)

**Exit criteria:** A map can go JSON → text → JSON and still open in RPG Maker MZ with behavior unchanged for the supported command set.

---

## Phase 4 — Switch / variable ID reassign (apply)

**Goal:** Bulk change of numeric IDs used by events (not merely labels in `System.json`), on top of the Phase 1 scanner.

Example need: every `Set Switch 10` and every `If Switch 10` becomes ID 47.

- [ ] Preview (CLI first) listing every hit, grouped by file; "this changes nothing yet" is explicit
- [ ] Conflict checks: refuse a **new ID that is already used**; refuse (or, later, split) a range that contains the ID; warn about dynamic references that mention the old ID
- [ ] One walker for scanning and rewriting; each hit carries the exact parameter slot to change
- [ ] Backups under a project-local folder before any write; one backup per operation
- [ ] Per-file apply with rollback on failure; an Undo entry
- [ ] Signature check: refuse if files changed since the scan
- [ ] **Rescan after apply** and fail loudly unless: old ID has zero hits, new ID has exactly old + previous hits
- [ ] Optional: update labels in `System.json` (off by default)
- [ ] Batch: several old → new pairs in one pass (swaps and chains handled in one plan)

**Exit criteria:** Dry-run on a large project is reviewable; apply + undo on a disposable copy leaves the project loadable and logic consistent for the remapped ID, and the rescan check passes.

**Known limits (documented, not hidden):** save files made before the change keep the old ID; plugin code is not rewritten; plugin parameters and plugin command arguments are only handled when the plugin declares them as a switch or variable.

---

## Phase 5 — Dialogue / text → events (exploratory)

**Goal:** Help turn structured dialogue or simple scripts into event command lists.

Inspiration (prior art, not a dependency):

- Text-to-frame style tools that expand dialogue into Show Text / choices / waits

Planned exploration:

- [ ] Minimal input format (e.g. markdown-like or YAML scenes)
- [ ] Emit Show Text, face/name boxes, simple choices, waits
- [ ] Insert generated lists into a target event page (or produce a standalone snippet)
- [ ] Keep scope small: no full quest graph, no battle logic in v1

**Exit criteria:** A short sample scene file produces a command list that round-trips through Phase 3 and plays correctly in-engine.

---

## Phase 6 — Polish & integration

- [ ] Unified CLI (`scan`, `print`, `parse`, `reassign-dry-run`, `reassign-apply`)
- [ ] Optional thin GUI later (not required for usefulness)
- [ ] Cross-links / optional interop notes with rpg-asset-tools (e.g. “open this map’s assets”)
- [ ] Packaging and versioned releases

---

## Brainstorm — ideas worth considering later

These are **not** commitments. Capture only.

| Idea | Notes |
|------|--------|
| Diff two versions of a map in readable form | Easier code-review of story changes |
| “Where is switch N used?” report | This is Phase 1 now; it can ship on its own |
| Batch reassign from a CSV (old_id → new_id) | Power-user workflow after single-ID path works |
| Plugin command registry | Optional YAML/JSON describing `@command` shapes for prettier plugin lines |
| Plugin command registry also for ID roles | Lets reassign handle plugin arguments declared as switch / variable |
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
2. Switch/variable reassign has a dry-run that a careful user trusts enough to apply on a copy, and a rescan proves the result.
3. Failures are visible (parse errors, unsupported codes, dynamic refs) rather than silent.
4. The tool never claims to support more command shapes than the tests cover.

---

*Last updated: phases reordered so the command table and the read-only ID scan come before the text round trip (the ID reassign is the concrete request). Adjust phases as implementation teaches us what is hard.*
