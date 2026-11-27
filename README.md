# RPG Story Adjuster

Tools for working with **RPG Maker MZ event and story data** — the parts that live inside `data/*.json` as command lists, conditions, switches, and variables.

This project is a sibling to [rpg-asset-tools](https://github.com/volpison/rpg-asset-tools).  
Asset Tools deals with files, names, references, and audio.  
**Story Adjuster** deals with event logic and human-editable representations of that logic.

## Goals

| Goal | Description |
|------|-------------|
| **Readable events** | Convert cryptic command JSON into a clear, line-oriented text form (and back) |
| **Safe ID reassign** | Find, and optionally remap, switch / variable numeric IDs across a project, with a proof that nothing was missed |
| **AI- and human-friendly editing** | Let people (or agents) edit story data in a form that is easier to reason about, then emit valid MZ JSON again |
| **Round-trip safety** | After convert → edit → convert-back, RPG Maker MZ must still load the project, and what was not edited must not change |

## Non-goals

- Replacing the RPG Maker MZ editor
- Asset rename / move / orphan detection (see **rpg-asset-tools**)
- Full visual event scripting UI (at least not in early phases)
- Guaranteeing compatibility with every third-party plugin’s custom command shapes

## Relationship to RPG Maker MZ

RPG Maker MZ stores events as lists of commands, for example:

```json
{"code": 122, "indent": 1, "parameters": [308, 308, 2, 0, 100]}
```

That is *Control Variables*: variable 308 (first and last of the range), operation 2 (subtract), operand type 0 (a constant), value 100.
Story Adjuster aims to present it as something closer to:

```text
Variable[308] -= 100
```

…and to turn the readable form back into the exact JSON structure the engine expects.

## How it will be built

- **One table of event commands.** Every command code, with the role of each parameter (switch ID, variable ID, text, script, …). Printing, parsing and ID scanning all read the same table, so they cannot disagree about where an ID hides.
- **Nothing is lost.** A command the tool does not know is kept as a raw JSON node, so plugin commands survive a round trip untouched.
- **Only what you edit changes.** Files and events you did not touch stay byte-for-byte identical, so a story change is a small, reviewable Git diff.
- **Dry-run first.** Scans and previews never write. Any write makes a backup first, can be undone, and is checked afterwards by scanning again.
- **Command line first.** The core is plain Python with no GUI; a window can come later.

## Status

Early design. See [ROADMAP.md](ROADMAP.md) for planned phases.

## License

MIT (see [LICENSE](LICENSE)).

This project is not affiliated with or endorsed by Gotcha Gotcha Games.  
“RPG Maker” is a registered trademark of Gotcha Gotcha Games Inc.
