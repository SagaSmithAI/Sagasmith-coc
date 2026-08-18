# Investigation, clues, Luck, and Push

## Information boundary

Separate:

- Keeper-only authored truth;
- immediately perceivable evidence;
- supplementary information from an action/check;
- per-actor learned or believed knowledge;
- public/party information after an actual sharing event.

A clue heading marks authored possibility, not automatic discovery. Conversely,
do not roll when the source makes the evidence obvious for the stated method.

## Pending-check state machine

~~~text
none -> open -> spend_luck -> settle -> history
             -> push       -> settle -> history
             -> settle                  history
             -> abort                   history
~~~

One actor has at most one pending check. Always query pending state after
interruption, restart, revision conflict, or uncertain transport result.

## Open a single check

Supply:

- source: concise source/scene basis;
- goal: exact intended result;
- trait_kind: skill, characteristic, or luck;
- trait_name: current sheet key;
- difficulty: regular, hard, or extreme;
- bonus_dice and penalty_dice.

Use current campaign and character revisions plus an exact-request idempotency
key. The runtime reads the threshold from the current sheet; never inject it.

## Open a combined check

Supply traits instead of one trait plus explicit requirement any or all. Use one
roll for two to eight current sheet traits. Each component retains its own
difficulty and outcome. The runtime computes exact aggregate Luck cost and marks
each eligible successful skill at settle.

The Keeper decides any/all from the action's meaning before the roll. Do not
choose the requirement after seeing the result.

## Spend Luck

- The campaign must enable the optional Spending Luck rule.
- Present the returned exact available action and current Luck to the player.
- Submit only the player's chosen positive amount.
- Do not spend more than current Luck or pretend to purchase an illegal result.
- After Luck changes the character revision, use the returned revisions for
  settle.

## Push

Before push, record:

- justification: how the actor changes/intensifies the attempt;
- failure_consequence: the concrete worse outcome already accepted as the stake;
- any changed trait/difficulty/dice modifiers justified by source/fiction.

Do not Push a check the runtime marks ineligible. A pushed result cannot then
spend Luck. The Keeper applies the declared consequence only if the pushed
outcome calls for it, then records it in continuity.

## Settle and commit meaning

Settle moves the mechanical check to bounded history and may mark development.
It does not decide clue text, audience, NPC response, or scene transition.

After settle:

1. interpret outcome from exact source/current context;
2. call memory_change commit with actual event/facts/ActorKnowledge;
3. update the correct party/group/player scene scope;
4. narrate only safe information.

If the continuity call fails, query check history and continuity before retrying
the semantic commit. Do not reroll.

## Multiple investigators

Use independent pending checks per actor when several investigators try. Another
investigator may attempt failed supplementary parts when the source/situation
allows. Do not combine their successes into a majority rule.

## Group Luck

1. Supply the exact present participant actor ids to group_luck_query.
2. The runtime reads current Luck and returns the lowest candidate(s).
3. If tied, the Keeper explicitly selects one returned lowest candidate.
4. group_luck_check rolls once from the campaign stream.
5. Commit the source-specific group consequence separately.

Group Luck does not spend the selected actor's Luck.

## Essential clues

Keep multiple viable discovery routes for plot-critical revelations. When a roll
fails, preserve playability by applying source-consistent cost, delay, danger,
partial detail, or alternate route. Never fabricate the clue or nullify player
choices merely to force a planned plot.
