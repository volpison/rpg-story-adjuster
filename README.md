# RPG Story Adjuster

Tools for working with **RPG Maker MZ event and story data** — the parts that live inside `data/*.json` as command lists, conditions, switches, and variables.

This project is a sibling to [rpg-asset-tools](https://github.com/volpison/rpg-asset-tools).  
Asset Tools deals with files, names, references, and audio.  
**Story Adjuster** deals with event logic and human-editable representations of that logic.

## Goals

| Goal | Description |
|------|-------------|
| **Readable events** | Convert cryptic command JSON into a clear, line-oriented text form (and back) |
| **Safe ID reassign** | Find and optionally remap switch / variable numeric IDs across a project |
| **AI- and human-friendly editing** | Let people (or agents) edit story data in a form that is easier to reason about, then emit valid MZ JSON again |
| **Round-trip safety** | After convert → edit → convert-back, RPG Maker MZ must still load the project |

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

Story Adjuster aims to present that as something closer to:

```text
Variable[100] -= 308
```

…and to turn the readable form back into the exact JSON structure the engine expects.

## Status

Early design. See [ROADMAP.md](ROADMAP.md) for planned phases.

## License

MIT (see [LICENSE](LICENSE)).

This project is not affiliated with or endorsed by Gotcha Gotcha Games.  
“RPG Maker” is a registered trademark of Gotcha Gotcha Games Inc.
