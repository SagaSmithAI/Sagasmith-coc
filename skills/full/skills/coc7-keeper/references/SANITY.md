# SAN and insanity settlement

Use coc_sanity_check for one source-explicit SAN encounter. Do not subtract SAN
in prose or replace the dedicated transaction with a raw d100.

## Required inputs

- actor_id and current character revision;
- current campaign revision;
- exact success_loss and failure_loss expressions from source;
- concise trigger/source description;
- context real_time or summary;
- stable exact-request idempotency key.

The tool owns the SAN roll, selected loss expression, loss roll, sheet update,
SAN maximum invariant, daily loss tracking, applicable INT check/bout state,
campaign random receipt, and revisions as one transaction.

## Agent responsibilities

- Decide whether the source trigger is actually perceived and understood by
  this actor.
- Do not call the mechanic for an actor who did not encounter the trigger.
- Use real_time for an immediate scene encounter and summary only when the
  source/workflow calls for summarized resolution.
- Narrate symptoms and behavior from the returned mechanical state, current
  source, player agency, and audience.
- Record actual chronology and per-actor knowledge without exposing another
  actor's private bout or Keeper truth.

## Recovery and boundaries

After interruption, reread the actor and revision history before retrying; exact
idempotency replays the same settlement. Do not create a second encounter to
repair missing narration.

The current MCP does not provide granular therapy, aging, Luck recovery, Mythos
study, or long-term institution workflows. Keep them source-bound and do not
claim atomic engine support until a dedicated mechanic exists.
