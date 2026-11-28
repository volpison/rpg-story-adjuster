# 0001 - Command table shape

**Status:** accepted (Phase 0)

## Context
The roadmap's guiding principle #6 says "one command table is the source of
truth" - every command code with the role of every parameter. A flat
`code -> [roles]` mapping is insufficient because some codes (Control Variables
122, Conditional Branch 111, Transfer Player 201) have parameter roles that
depend on the values of other parameters.

## Decision
Each `CommandSpec` carries a callable `roles(params) -> list[Role]`. Simple
codes use `fixed_roles(...)`. Conditional codes supply a resolver. The scanner
(Phase 1), printer (Phase 2) and parser (Phase 3) all consume `spec.roles(params)`;
no other module hard-codes where an ID can hide.

## Consequences
- Adding a new code is one registration, no branching logic elsewhere.
- Resolvers must return roles for **every** case the code can take, or the
  scanner will silently miss hits. Tests must cover every branch kind that
  a registered code supports.
- Unregistered codes are treated as fully `raw` (safe fallback - not scanned,
  not rewritten). Registering more codes is additive.
