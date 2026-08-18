# Investigator, NPC, and creature lifecycle

Use validated character_query/character_change tools in Lobby. Do not persist a
player investigator before the authorized player confirms the complete draft.

## Create

1. Read campaign settings: Classic/Pulp, era, locale, optional rules, and source.
2. Gather the complete sheet required by the current sagasmith-coc schema.
3. Preserve source values and campaign-approved unknown extension fields.
4. Present characteristics, HP/MP/SAN/Luck, SAN maximum, MOV, DB/Build, Dodge,
   skills, weapons, conditions, occupation/archetype, development state,
   biography/backstory, inventory/books, money/Credit Rating, Mythos, and Pulp
   talents as applicable.
5. Wait for human confirmation.
6. character_change create under the authenticated principal.
7. Reread and verify the created identity, sheet, revision, campaign, type, and
   actor control.

## Instantiate a Pack preset

When an imported current-schema Content Pack binds an investigator actor as
`preset_pc`:

1. Keep the template in the Pack library; do not edit it into campaign state.
2. Read the successful content_pack import response and select the template id
   from actor_map using the Pack actor id.
3. In Lobby, call character_change(action="instantiate") with the campaign id
   and data.template_id. data.name and data.player_name are optional reviewed
   overrides.
4. Reread the resulting campaign-local investigator and verify that the source
   sheet was preserved. The Keeper receives actor control at instantiation.
5. If the Pack or source requires a rolled starting value that is intentionally
   absent from the reusable template, use the authoritative mechanic after
   instantiation. For Quick-Start Luck, roll 3D6 with coc_dice_roll and update
   Luck to the receipt total multiplied by five; never pre-roll locally.
6. Grant the new actor to the authenticated player with
   campaign_change(action="grant_actor"), then verify the player's actor-scoped
   read before entering Play.

Instantiate only investigator templates. Pack NPCs and creatures are imported
directly as campaign cast and are not valid character_change templates.

NPCs and creatures may be Keeper-confirmed. An executable Module actor requires
a reviewed source-preserving statblock; missing mechanical values remain missing
and may keep the actor narrative-only.

## Update

Read the complete current character and revision. Apply a reviewed complete
sheet update without discarding unknown or campaign-approved fields. Use
dedicated SAN/HP/investigation/development/encounter tools when they own the
mechanic; do not bypass their transaction with generic character update.

## Development

Successful eligible investigation skills are marked only when a pending check is
settled. At an authorized Lobby boundary:

1. development_query the actor;
2. show checked skills and ineligible entries;
3. verify campaign and character revisions;
4. development_settle once with a source label and stable key;
5. reread the actor and preserve the receipt.

The runtime rolls each eligible checked skill, increases on the correct
development result, caps values, applies first mastery SAN where applicable,
clears all check marks, and stores history. Cthulhu Mythos is excluded from
ordinary development.

Do not infer aging, Credit Rating, Luck recovery, therapy, Mythos advancement,
or Pulp changes from ordinary development; use a future dedicated/source-bound
workflow.
