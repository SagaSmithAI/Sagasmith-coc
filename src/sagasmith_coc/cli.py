"""Portable CoC 7e JSON CLI used by Skill-based agent platforms."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sagasmith_core import (
    CampaignService,
    CharacterService,
    EventService,
    MemoryService,
    ModuleService,
    RevisionService,
    RuleProfileService,
    RuleService,
    SnapshotService,
)
from sagasmith_core.documents import converter_for
from sagasmith_core.modules import MarkdownModuleParser

from sagasmith_coc import __version__
from sagasmith_coc.engine.checks.chase import resolve_chase_action, resolve_chase_speed_check
from sagasmith_coc.engine.checks.combat import resolve_melee_attack, resolve_ranged_attack
from sagasmith_coc.engine.checks.sanity import resolve_sanity_loss, roll_bout_of_madness
from sagasmith_coc.engine.checks.skill import resolve_opposed_check, resolve_skill_check
from sagasmith_coc.engine.development import (
    resolve_luck_development,
    resolve_skill_development,
)
from sagasmith_coc.engine.dice.rolls import roll_d100, roll_dice_expression
from sagasmith_coc.module_profile import CocModuleProfile
from sagasmith_coc.runtime import database, dense_components
from sagasmith_coc.system import COC7E, validate_investigator_sheet


class CliError(RuntimeError):
    def __init__(self, code: str, message: str, *, exit_code: int = 5) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


def _dict(raw: str | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if raw.startswith("@"):
        raw = Path(raw[1:]).expanduser().read_text(encoding="utf-8")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CliError("invalid_json", str(exc), exit_code=2) from exc
    if not isinstance(value, dict):
        raise CliError("object_required", "expected a JSON object", exit_code=2)
    return value


def _require(value: Any, name: str) -> Any:
    if value is None or value == "":
        raise CliError("argument_required", f"--{name} is required", exit_code=2)
    return value


def _campaign_revision(revisions, before, after, operation: str) -> None:
    fields = ("name", "status", "description", "settings", "state", "revision")
    revisions.record(
        before.id,
        operation=operation,
        entity_type="campaign",
        entity_id=before.id,
        before={name: getattr(before, name) for name in fields},
        after={name: getattr(after, name) for name in fields},
    )


def _character_revision(revisions, before, after, operation: str) -> None:
    if before.campaign_id is None:
        return
    fields = ("name", "player_name", "summary", "sheet", "notes", "revision")
    revisions.record(
        before.campaign_id,
        operation=operation,
        entity_type="character",
        entity_id=before.id,
        before={name: getattr(before, name) for name in fields},
        after={name: getattr(after, name) for name in fields},
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sagasmith-coc")
    parser.add_argument("group")
    parser.add_argument("action", nargs="?")
    for name in (
        "campaign",
        "id",
        "name",
        "status",
        "description",
        "locale",
        "ruleset",
        "settings",
        "state",
        "payload",
        "metadata",
        "sheet",
        "notes",
        "type",
        "player",
        "summary",
        "subject",
        "content",
        "path",
        "output",
        "source-key",
        "title",
        "version",
        "publication",
        "query",
        "chunk",
        "scene",
        "module",
        "label",
        "expression",
        "difficulty",
        "source",
        "scope",
    ):
        parser.add_argument(f"--{name}")
    parser.add_argument("--publications", nargs="*")
    parser.add_argument("--slot", type=int)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--progress", type=int, default=0)
    parser.add_argument("--threshold", type=int)
    parser.add_argument("--roll", type=int)
    parser.add_argument("--bonus-dice", type=int, default=0)
    parser.add_argument("--penalty-dice", type=int, default=0)
    parser.add_argument("--current-san", type=int)
    parser.add_argument("--san-max", type=int)
    parser.add_argument("--loss", type=int)
    parser.add_argument("--daily-loss", type=int, default=0)
    parser.add_argument("--mov", type=int)
    parser.add_argument("--distance", type=int, default=0)
    parser.add_argument("--current-value", type=int)
    parser.add_argument("--dense", action="store_true")
    parser.add_argument("--pulp", action="store_true")
    parser.set_defaults(scope="party")
    return parser


def _dispatch(args) -> Any:
    if args.group == "version":
        return {"version": __version__, "system_id": COC7E.id}
    if args.group == "capabilities":
        return {
            "system_id": COC7E.id,
            "rulesets": ["classic", "pulp"],
            "commands": [
                "campaign",
                "investigator",
                "event",
                "rules",
                "module",
                "save",
                "memory",
                "state",
                "roll",
                "check",
                "sanity",
                "combat",
                "chase",
                "development",
            ],
            "agent_interface": "skill+json-cli",
        }

    db = database()
    try:
        if args.group == "database" and args.action == "upgrade":
            db.upgrade_schema()
            return {"upgraded": True, "database_url": db.url}
        if args.group == "doctor":
            embedder, vectors = dense_components()
            return {
                "ok": True,
                "version": __version__,
                "database_url": db.url,
                "database_ready": True,
                "dense_enabled": embedder is not None,
                "embedding_model": embedder.model_name if embedder else None,
                "vector_enabled": bool(vectors and vectors.enabled),
                "commercial_rulebooks_bundled": False,
            }

        campaigns = CampaignService(db)
        characters = CharacterService(db)
        profiles = RuleProfileService(db)
        events = EventService(db)
        rules = RuleService(db)
        modules = ModuleService(db)
        saves = SnapshotService(db)
        memories = MemoryService(db)
        revisions = RevisionService(db)

        if args.group == "campaign":
            if args.action in {"create", "start"}:
                campaign = campaigns.create(
                    system_id=COC7E.id,
                    name=_require(args.name, "name"),
                    description=args.description or "",
                    settings={**COC7E.campaign_defaults, **_dict(args.settings)},
                    state=_dict(args.state),
                )
                profile = profiles.set(
                    campaign.id,
                    edition="7e",
                    locale=args.locale or "zh",
                    publications=args.publications or [],
                    options={"ruleset": args.ruleset or ("pulp" if args.pulp else "classic")},
                )
                result = {"campaign": asdict(campaign), "rule_profile": asdict(profile)}
                if args.action == "start":
                    result["snapshot"] = asdict(
                        saves.create(campaign.id, label="Initial state")
                    )
                return result
            if args.action == "list":
                return {
                    "campaigns": [
                        asdict(item)
                        for item in campaigns.list(system_id=COC7E.id, status=args.status)
                    ]
                }
            if args.action == "show":
                campaign_id = _require(args.campaign or args.id, "campaign")
                profile = profiles.get(campaign_id)
                return {
                    "campaign": asdict(campaigns.get(campaign_id)),
                    "rule_profile": asdict(profile) if profile else None,
                }
            if args.action in {"update", "archive"}:
                campaign_id = _require(args.campaign or args.id, "campaign")
                before = campaigns.get(campaign_id)
                updated = campaigns.update(
                        campaign_id,
                        name=args.name,
                        status="archived" if args.action == "archive" else args.status,
                        description=args.description,
                        settings=_dict(args.settings) if args.settings else None,
                        state=_dict(args.state) if args.state else None,
                    )
                _campaign_revision(revisions, before, updated, "campaign.update")
                return asdict(updated)
            if args.action == "delete":
                campaign_id = _require(args.campaign or args.id, "campaign")
                campaigns.delete(campaign_id)
                return {"deleted": campaign_id}
            if args.action == "rules-get":
                value = profiles.get(_require(args.campaign, "campaign"))
                return asdict(value) if value else None
            if args.action == "rules-set":
                return asdict(
                    profiles.set(
                        _require(args.campaign, "campaign"),
                        edition="7e",
                        locale=args.locale or "zh",
                        publications=args.publications or [],
                        options={"ruleset": args.ruleset or "classic"},
                    )
                )

        if args.group in {"investigator", "character"}:
            if args.action == "validate":
                return validate_investigator_sheet(_dict(args.sheet))
            if args.action == "create":
                return asdict(
                    characters.create(
                        system_id=COC7E.id,
                        campaign_id=args.campaign,
                        name=_require(args.name, "name"),
                        character_type=args.type or "investigator",
                        player_name=args.player,
                        summary=args.summary or "",
                        sheet=validate_investigator_sheet(_dict(args.sheet)),
                        notes=_dict(args.notes),
                    )
                )
            if args.action == "list":
                return {
                    "investigators": [
                        asdict(item)
                        for item in characters.list(
                            system_id=COC7E.id,
                            campaign_id=args.campaign,
                            character_type=args.type,
                        )
                    ]
                }
            if args.action == "show":
                return asdict(characters.get(_require(args.id, "id")))
            if args.action == "update":
                sheet = _dict(args.sheet) if args.sheet else None
                character_id = _require(args.id, "id")
                before = characters.get(character_id)
                updated = characters.update(
                        character_id,
                        name=args.name,
                        player_name=args.player,
                        summary=args.summary,
                        sheet=(
                            validate_investigator_sheet(sheet)
                            if sheet is not None
                            else None
                        ),
                        notes=_dict(args.notes) if args.notes else None,
                    )
                _character_revision(revisions, before, updated, "investigator.update")
                return asdict(updated)
            if args.action in {"bind", "unbind"}:
                return asdict(
                    characters.bind(
                        _require(args.id, "id"),
                        args.campaign if args.action == "bind" else None,
                    )
                )

        if args.group == "event":
            if args.action == "add":
                return asdict(
                    events.add(
                        _require(args.campaign, "campaign"),
                        event_type=args.type or "investigation",
                        summary=_require(args.summary, "summary"),
                        payload=_dict(args.payload),
                    )
                )
            if args.action == "list":
                return {
                    "events": [
                        asdict(item)
                        for item in events.list(
                            _require(args.campaign, "campaign"),
                            limit=args.limit,
                        )
                    ]
                }

        if args.group == "rules":
            embedder, vectors = dense_components() if args.dense else (None, None)
            if args.action in {"sources", "status"}:
                return {"sources": rules.sources(system_id=COC7E.id, edition="7e")}
            if args.action == "ingest":
                path = Path(_require(args.path, "path")).expanduser().resolve()
                document = converter_for(path).convert(path)
                return asdict(
                    rules.ingest(
                        system_id=COC7E.id,
                        source_key=args.source_key or path.name,
                        title=args.title or path.stem,
                        content=document.content,
                        edition="7e",
                        locale=args.locale or "zh",
                        version=args.version or "",
                        publication_id=args.publication or "",
                        authority="user-provided",
                        metadata={"source_path": str(path), **document.metadata},
                        embedder=embedder,
                        vector_store=vectors,
                    )
                )
            if args.action == "search":
                locale = args.locale
                publications = list(args.publications or [])
                if args.campaign and (profile := profiles.get(args.campaign)):
                    locale = locale or profile.locale
                    publications = publications or list(profile.publications)
                return {
                    "hits": [
                        asdict(item)
                        for item in rules.search(
                            system_id=COC7E.id,
                            query=_require(args.query, "query"),
                            edition="7e",
                            locale=locale,
                            publications=publications,
                            top_k=args.limit,
                            embedder=embedder,
                            vector_store=vectors,
                        )
                    ]
                }
            if args.action == "expand":
                return rules.expand(_require(args.chunk, "chunk"))

        if args.group == "module":
            embedder, vectors = dense_components() if args.dense else (None, None)
            parser = MarkdownModuleParser(profile=CocModuleProfile())
            if args.action == "inspect":
                path = Path(_require(args.path, "path")).expanduser().resolve()
                document = converter_for(path).convert(path)
                parsed = parser.parse(document.content)
                return {
                    "source_path": str(path),
                    "warnings": list(document.warnings),
                    "chapters": len(parsed),
                    "scenes": sum(len(item.scenes) for item in parsed),
                }
            if args.action == "ingest":
                return asdict(
                    modules.ingest_path(
                        campaign_id=_require(args.campaign, "campaign"),
                        path=_require(args.path, "path"),
                        source_key=args.source_key,
                        title=args.title,
                        parser=parser,
                        embedder=embedder,
                        vector_store=vectors,
                    )
                )
            if args.action == "list":
                return {"modules": modules.list(_require(args.campaign, "campaign"))}
            if args.action == "search":
                return {
                    "hits": [
                        asdict(item)
                        for item in modules.search(
                            campaign_id=_require(args.campaign, "campaign"),
                            query=_require(args.query, "query"),
                            top_k=args.limit,
                            embedder=embedder,
                            vector_store=vectors,
                        )
                    ]
                }
            if args.action == "expand":
                return modules.expand(_require(args.chunk, "chunk"))
            if args.action == "read-scene":
                return modules.read_scene(
                    _require(args.campaign, "campaign"),
                    _require(args.scene, "scene"),
                )
            if args.action == "current":
                return {
                    "scene": modules.current_scene(
                        _require(args.campaign, "campaign"),
                        scope_id=args.scope,
                    )
                }
            if args.action in {"index", "export-scenes"}:
                scenes = modules.scene_index(
                    _require(args.campaign, "campaign"),
                    module_id=args.module,
                )
                result = {"campaign_id": args.campaign, "scenes": scenes}
                if args.output:
                    target = Path(args.output).expanduser().resolve()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(
                        json.dumps(result, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    result["output"] = str(target)
                return result
            if args.action in {"set-scene", "set-progress"}:
                return modules.set_scene_progress(
                    campaign_id=_require(args.campaign, "campaign"),
                    scene_id=_require(args.scene, "scene"),
                    status=args.status or "current",
                    progress=args.progress,
                    state=None if args.state is None else _dict(args.state),
                    scope_id=args.scope,
                )

        if args.group == "save":
            campaign_id = _require(args.campaign, "campaign")
            if args.action == "create":
                return asdict(saves.create(campaign_id, label=args.label or ""))
            if args.action == "list":
                return {"snapshots": [asdict(item) for item in saves.list(campaign_id)]}
            if args.action == "show":
                return saves.get(campaign_id, _require(args.slot, "slot"))
            if args.action == "verify":
                return {"valid": saves.verify(campaign_id, _require(args.slot, "slot"))}
            if args.action == "restore":
                return asdict(saves.restore(campaign_id, _require(args.slot, "slot")))
            if args.action == "regenerate-recap":
                return saves.regenerate_recap(
                    campaign_id,
                    _require(args.slot, "slot"),
                )
            if args.action == "lineage":
                return {
                    "lineage": [
                        asdict(item) for item in saves.lineage(campaign_id, args.slot)
                    ]
                }

        if args.group == "memory":
            campaign_id = _require(args.campaign, "campaign")
            if args.action == "add":
                return asdict(
                    memories.add(
                        campaign_id,
                        content=_require(args.content, "content"),
                        kind=args.type or "clue",
                        subject=args.subject or "",
                        metadata=_dict(args.metadata),
                    )
                )
            if args.action == "list":
                return {
                    "memories": [
                        asdict(item) for item in memories.list(campaign_id, kind=args.type)
                    ]
                }
            if args.action == "search":
                return {
                    "memories": [
                        asdict(item)
                        for item in memories.search(
                            campaign_id,
                            _require(args.query, "query"),
                            limit=args.limit,
                        )
                    ]
                }
            if args.action in {"scope", "status"}:
                values = memories.list(campaign_id, kind=args.type)
                return {
                    "campaign_id": campaign_id,
                    "count": len(values),
                    "memories": [asdict(item) for item in values],
                }

        if args.group == "state":
            campaign_id = _require(args.campaign, "campaign")
            if args.action == "undo":
                return asdict(revisions.undo(campaign_id))
            if args.action == "redo":
                return asdict(revisions.redo(campaign_id))
            if args.action == "history":
                return {
                    "revisions": [
                        asdict(item) for item in revisions.history(campaign_id, limit=args.limit)
                    ]
                }

        if args.group == "roll":
            if args.action == "d100":
                return roll_d100(args.bonus_dice, args.penalty_dice)
            if args.action == "dice":
                return roll_dice_expression(_require(args.expression, "expression"))
        if args.group == "check" and args.action == "skill":
            rolled = args.roll or roll_d100(args.bonus_dice, args.penalty_dice)["total"]
            return resolve_skill_check(
                rolled,
                _require(args.threshold, "threshold"),
                difficulty=args.difficulty or "regular",
                bonus_dice=args.bonus_dice,
                penalty_dice=args.penalty_dice,
            )
        if args.group == "check" and args.action == "opposed":
            options = _dict(args.payload)
            return resolve_opposed_check(
                int(_require(options.get("attacker_roll"), "payload.attacker_roll")),
                int(
                    _require(
                        options.get("attacker_threshold"),
                        "payload.attacker_threshold",
                    )
                ),
                int(_require(options.get("defender_roll"), "payload.defender_roll")),
                int(
                    _require(
                        options.get("defender_threshold"),
                        "payload.defender_threshold",
                    )
                ),
                tie_breaker=str(options.get("tie_breaker", "higher-skill")),
            )
        if args.group == "sanity":
            if args.action == "loss":
                options = _dict(args.payload)
                return resolve_sanity_loss(
                    _require(args.current_san, "current-san"),
                    args.san_max or 99,
                    _require(args.loss, "loss"),
                    daily_loss_accumulated=args.daily_loss,
                    pulp_rules=args.pulp,
                    source=args.source or "",
                    int_check_success=options.get("int_check_success"),
                )
            if args.action == "bout":
                return roll_bout_of_madness()
        if args.group == "combat":
            rolled = args.roll or roll_d100(args.bonus_dice, args.penalty_dice)["total"]
            options = _dict(args.payload)
            if args.action == "melee":
                return resolve_melee_attack(
                    rolled,
                    _require(args.threshold, "threshold"),
                    bonus_dice=args.bonus_dice,
                    penalty_dice=args.penalty_dice,
                    **options,
                )
            if args.action == "ranged":
                return resolve_ranged_attack(
                    rolled,
                    _require(args.threshold, "threshold"),
                    _require(args.expression, "expression"),
                    bonus_dice=args.bonus_dice,
                    penalty_dice=args.penalty_dice,
                    **options,
                )
        if args.group == "chase":
            if args.action == "speed":
                return resolve_chase_speed_check(
                    args.roll or roll_d100()["total"],
                    _require(args.mov, "mov"),
                    difficulty=args.difficulty or "regular",
                )
            if args.action == "act":
                return resolve_chase_action(
                    args.type or "obstacle",
                    _require(args.threshold, "threshold"),
                    args.roll or roll_d100()["total"],
                    distance=args.distance,
                )
        if args.group == "development":
            if args.action == "skill":
                return resolve_skill_development(
                    _require(args.current_value, "current-value")
                )
            if args.action == "luck":
                return resolve_luck_development(
                    _require(args.current_value, "current-value")
                )

        raise CliError(
            "unknown_command",
            f"unknown command: {args.group} {args.action or ''}".strip(),
            exit_code=2,
        )
    finally:
        db.dispose()


def _error(exc: Exception) -> tuple[str, int]:
    if isinstance(exc, CliError):
        return exc.code, exc.exit_code
    if isinstance(exc, LookupError):
        return "not_found", 3
    if isinstance(exc, ValueError):
        return "invalid_value", 2
    return "internal_error", 10


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    compact = "--json" in values
    values = [value for value in values if value != "--json"]
    command = ".".join(values[:2])
    try:
        args = _parser().parse_args(values)
        data = _dispatch(args)
        envelope = {
            "ok": True,
            "data": data,
            "error": None,
            "meta": {"command": command, "version": __version__},
        }
        code = 0
    except SystemExit:
        raise
    except Exception as exc:
        error_code, code = _error(exc)
        envelope = {
            "ok": False,
            "data": None,
            "error": {"code": error_code, "message": str(exc)},
            "meta": {"command": command, "version": __version__},
        }
    print(
        json.dumps(
            envelope,
            # Keep stdout portable on Windows hosts whose console still uses GBK.
            ensure_ascii=True,
            separators=(",", ":") if compact else None,
            indent=None if compact else 2,
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
