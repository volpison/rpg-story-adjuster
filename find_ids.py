"""Report which switch and variable IDs are used, by hit count."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, ".")
from rpg_story_adjuster.walker import iter_project_commands
from rpg_story_adjuster.commands import table


def main(project_root: str) -> None:
    root = Path(project_root)
    switches: Counter = Counter()
    variables: Counter = Counter()
    for cmd in iter_project_commands(root):
        spec = table.get(cmd.code)
        if spec is None:
            continue
        for role in spec.roles(cmd.parameters):
            if role.kind in ("switch", "switch_range_start"):
                try:
                    switches[cmd.parameters[role.index]] += 1
                except IndexError:
                    pass
            elif role.kind in ("variable", "variable_range_start"):
                try:
                    variables[cmd.parameters[role.index]] += 1
                except IndexError:
                    pass

    print(f"switches used ({len(switches)} distinct):")
    for sid, n in sorted(switches.items()):
        print(f"  switch {sid:3d}  ({n} reference{'s' if n != 1 else ''})")
    print(f"\nvariables used ({len(variables)} distinct):")
    for vid, n in sorted(variables.items()):
        print(f"  var    {vid:3d}  ({n} reference{'s' if n != 1 else ''})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: find_ids.py <project-root>", file=sys.stderr)
        raise SystemExit(2)
    main(sys.argv[1])