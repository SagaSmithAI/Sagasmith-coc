# Keeper mechanic ownership

This reference is an operating boundary, not a replacement rulebook. Use
user-authorized source evidence and the deterministic sagasmith-coc engine.

## Source order

1. Active finalized Module Pack for scenario-specific truth.
2. Active authorized rule/content Pack when available.
3. Current campaign profile and validated actor sheet.
4. Agent Keeper ruling for narrative facts the system intentionally leaves open.
5. Human input for player intent, permission, optional resource choices, and
   genuinely missing/conflicting evidence.

Never promote one source book's exception into reusable engine behavior.

## Choose the highest-level mechanic

| Need | Use |
|---|---|
| Live characteristic/skill/Luck check | investigation_check |
| Combined any/all check | investigation_check with traits |
| Group Luck | group_luck_query/check |
| Opposed or specialized one-shot resolution | coc_resolve |
| SAN encounter | coc_sanity_check |
| Non-combat damage/heal | coc_hp_change |
| Active Chase | chase tools |
| Active Combat | combat tools |
| Unowned raw roll | coc_dice_roll |

Higher-level tools read current actor values, own random receipts, validate
optional rules, update authoritative state, and preserve idempotency. Do not
replace them with arithmetic or a raw die roll.

## Investigation principles

- Describe player method and goal before selecting a trait.
- Give obvious/source-guaranteed information without a roll.
- Declare difficulty and ordinary failure consequence before open.
- Let the human choose Luck expenditure or Push.
- A Push requires a plausible intensified/changed approach and a known worse
  failure consequence.
- A combined check uses one roll and an explicit any/all requirement.
- Multiple actor attempts are independent; group Luck is a different rule.
- Settle the mechanic before committing clue meaning and audience.

## Success and failure

The engine owns d100 selection, bonus/penalty dice, success level, fumble,
difficulty, Luck legality/cost, Push legality, opposed tie handling, and
development eligibility. Use the returned result rather than re-deriving it.

The Agent owns what the result means in this situation. A failed investigation
may cost time, position, safety, completeness, or opportunity; it should not
erase the only indispensable clue.

## Standard versus semantic state

- Mechanical HP/SAN/Luck/skills/conditions: character sheet through MCP.
- Chase/Combat actions: encounter facade.
- Scene discovery/progress: module_change.
- Objective durable facts: memory.
- Chronology: event.
- Subjective information: ActorKnowledge.
- Narration: Agent output for the actual audience.

## Block only when required

Block for missing permission, unresolved player choice, stale authoritative
revision, conflicting/missing required source evidence, active incompatible
encounter, or mechanically indispensable data. Do not block for missing
portraits, optional presentation, advisory readiness, or a narrative fact the
Keeper is authorized to rule.
