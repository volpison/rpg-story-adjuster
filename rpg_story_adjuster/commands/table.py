from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Literal

RoleKind = Literal[
    "switch", "switch_range_start", "switch_range_end",
    "variable", "variable_range_start", "variable_range_end",
    "operand", "script", "text", "raw",
]


@dataclass(frozen=True)
class Role:
    index: int
    kind: RoleKind


@dataclass
class CommandSpec:
    code: int
    name: str
    _roles_fn: Callable[[list], list[Role]]

    def roles(self, params: list) -> list[Role]:
        return self._roles_fn(params)


def fixed_roles(*roles: Role) -> Callable[[list], list[Role]]:
    return lambda params: list(roles)


# ---- Resolvers for codes whose parameter roles are conditional ----

def _roles_122(params: list) -> list[Role]:
    """Control Variables: [start, end, operation, operand, operand_type]."""
    if len(params) < 5:
        return []
    roles = [
        Role(0, "variable_range_start"),
        Role(1, "variable_range_end"),
        Role(2, "raw"),          # operation (+= -= *= /= %=)
        Role(4, "raw"),          # operand_type
    ]
    operand_type = params[4]
    if operand_type == 1:        # operand is another variable ID
        roles.append(Role(3, "variable"))
    elif operand_type == 4:      # operand is a script string
        roles.append(Role(3, "script"))
    else:                        # constant / random range / game data
        roles.append(Role(3, "raw"))
    return roles


def _roles_111(params: list) -> list[Role]:
    """Conditional Branch: [branch_type, ...]."""
    if not params:
        return []
    t = params[0]
    if t == 0:                   # [0, switch_id, 0|1]
        return [Role(0, "raw"), Role(1, "switch"), Role(2, "raw")]
    if t == 1:                   # [1, var_id, comparison, operand, operand_type]
        roles = [Role(0, "raw"), Role(1, "variable"),
                 Role(2, "raw"), Role(3, "raw"), Role(4, "raw")]
        if len(params) > 4 and params[4] == 1:
            # operand is another variable ID (MZ rpg_objects.js case 1)
            roles[3] = Role(3, "variable")
        return roles
    if t == 2:                   # self switch
        return [Role(0, "raw"), Role(1, "raw"), Role(2, "raw")]
    if t == 12:                  # script
        return [Role(0, "raw"), Role(1, "script")]
    # Other branch kinds (timer/actor/enemy/character/gold/button/vehicle/...) TBD.
    return [Role(0, "raw")]


def _roles_201(params: list) -> list[Role]:
    """Transfer Player: [designation, mapId, x, y, direction, fade].

    designation 0 = direct (literals); 1 = by variable (IDs at slots 1..3).
    """
    if not params:
        return []
    roles = [Role(0, "raw"), Role(4, "raw"), Role(5, "raw")]
    if params[0] == 1:
        roles += [Role(1, "variable"), Role(2, "variable"), Role(3, "variable")]
    else:
        roles += [Role(1, "raw"), Role(2, "raw"), Role(3, "raw")]
    return roles


# ---- Registry ----

_REGISTRY: dict[int, CommandSpec] = {}


def _register(spec: CommandSpec) -> None:
    _REGISTRY[spec.code] = spec


_register(CommandSpec(
    121, "Control Switches",
    fixed_roles(
        Role(0, "switch_range_start"),
        Role(1, "switch_range_end"),
        Role(2, "raw"),
    ),
))
_register(CommandSpec(122, "Control Variables", _roles_122))
_register(CommandSpec(111, "Conditional Branch", _roles_111))

# Phase 1 additions
_register(CommandSpec(201, "Transfer Player", _roles_201))
_register(CommandSpec(355, "Script", fixed_roles(Role(0, "script"))))
_register(CommandSpec(655, "Script (cont.)", fixed_roles(Role(0, "script"))))
_register(CommandSpec(401, "Show Text (cont.)", fixed_roles(Role(0, "text"))))
_register(CommandSpec(102, "Show Choices", fixed_roles(Role(0, "text"))))
_register(CommandSpec(103, "Input Number", fixed_roles(Role(0, "variable"))))
_register(CommandSpec(104, "Select Item", fixed_roles(Role(0, "variable"))))

# TODO (Phase 1+): 203 Set Event Location, 125-129 Change Gold/Items/Weapons/
#   Armors, 285 Get Location Info, pictures, 402/403 choice branches, 405/505
#   move-route scripts. Register only when the parameter shapes are verified
#   against real data.


def get(code: int) -> CommandSpec | None:
    return _REGISTRY.get(code)


def codes() -> list[int]:
    return sorted(_REGISTRY)
