import sys
from pathlib import Path

sys.path.insert(0, ".")
from rpg_story_adjuster.walker import iter_project_commands
from rpg_story_adjuster.commands import table
from rpg_story_adjuster.scan import scan_project

root = Path(sys.argv[1])
total = 0
n25_raw = 0
n6_raw = 0
for cmd in iter_project_commands(root):
    total += 1
    if cmd.code == 121 and isinstance(cmd.parameters, list) and len(cmd.parameters) >= 2:
        if cmd.parameters[0] == 25 or cmd.parameters[1] == 25:
            n25_raw += 1
            print(f"  raw-25: {cmd.source.file} ev={cmd.source.event_id} "
                  f"idx={cmd.source.command_index} params={cmd.parameters}")
        if cmd.parameters[0] == 6 or cmd.parameters[1] == 6:
            n6_raw += 1

print(f"total commands walked: {total}")
print(f"raw code=121 containing 25: {n25_raw}")
print(f"raw code=121 containing 6:  {n6_raw}")
print(f"scan_project switch 25:     {len(scan_project(root, 'switch', 25).hits)}")
print(f"scan_project switch 6:      {len(scan_project(root, 'switch', 6).hits)}")
print(f"scan_project switch 101:    {len(scan_project(root, 'switch', 101).hits)}")