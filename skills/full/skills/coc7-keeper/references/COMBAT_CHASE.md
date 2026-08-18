# Authoritative Chase and Combat

Chase and Combat are mutually exclusive authoritative states. Both begin in Play
and must close through their dedicated end tools.

## Chase

### Start

Read exact participants and character revisions. Supply source, route/hazard
evidence when present, campaign revision, and one idempotency key. For a vehicle
participant, set participant_kind=vehicle and bind the reviewed source card with
source_id, name, and Build; use its source MOV for the participant. chase_start
owns speed checks, effective MOV, action points, initial order/positions, random
receipt, and Chase state.

Do not invent route geometry. Omit optional route data when the source leaves it
to Keeper judgment.

### Operate

Call chase_query before every action. Use only returned legal actions:

- move;
- check for an explicit hazard/barrier/task;
- speed_check when currently legal;
- end_turn.

Each action consumes authoritative Chase resources. Record narrative
consequences separately without duplicating positions/action points in memory.

### End

Use chase_end with escaped, caught, abandoned, or other plus a source-explicit
outcome. Refresh Play tools and settle actual scene continuity.

Current boundaries: vehicle identity, Build, and MOV are authoritative Chase
inputs, but collision/damage, elaborate multi-actor assistance, and
Chase-within-Combat mechanics remain source-backed Keeper rulings.

## Combat

### Start

Confirm no active Chase. Supply:

- exact participants and current character revisions;
- source;
- campaign revision and idempotency key;
- positioning_mode grid or agent;
- grid metric/unit only for grid.

Use grid only when authoritative coordinates are available. In agent mode,
provide no synthetic coordinates; the Keeper rules range, line of sight,
obstruction, and friendly-fire risk from current evidence.

combat_start owns order, ready-fire handling, participants, round/turn state,
phase transition, and revisions. Refresh schemas after tools/list_changed.

### Observe and act

Call combat_query before each turn/action.

- combat_action join/move/end_turn handles guarded non-attack state.
- combat_attack(open) creates an authoritative attack plus required defense or
  response choice.
- combat_attack(resolve) answers the exact pending choice and owns attack,
  damage, armor, HP/wound transition, ammunition/malfunction where implemented,
  random receipts, and revisions.
- combat_attack(abort) records an explicit cancellation; never use it to reroll.

Resolve/abort the pending attack before ending Combat or changing stale context.
Use coc_hp_change only for a separate legal non-attack damage/heal transition.

### End

Use combat_end with victory, escape, surrender, defeat, or other plus source.
It closes the encounter and returns to Play. Refresh tools, reread characters,
and commit actual consequences.

Authority boundary: the Agent/source explicitly decides maneuver intent and
effect, firing sequence, cover geometry, vehicle consequence, and when a
dying/healing interval occurs. Use the current Combat, Chase, coc_hp_change,
inventory, and continuity facades to settle the resulting mechanical state;
never invent geometry, timing, or source facts inside MCP.

## Recovery

After restart or uncertain transport:

1. read phase;
2. query the active Chase/Combat and pending choices;
3. inspect state revision receipt/history;
4. reuse an idempotency key only for the exact same request;
5. continue from returned legal state rather than reconstructing it from prose.
