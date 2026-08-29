from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from sagasmith_coc.playthrough import new_playthrough_manifest

from sagasmith_coc_mcp.actor_memory import select_actor_memory_context
from sagasmith_coc_mcp.config import McpConfig
from sagasmith_coc_mcp.npc_conversations import normalize_conversation_proposal
from sagasmith_coc_mcp.server import create_server


async def call(server, name: str, arguments: dict):
    if name == "character_change" and arguments.get("action") == "create":
        campaign = (
            await server.call_tool(
                "campaign_query",
                {"action": "get", "campaign_id": arguments["campaign_id"]},
            )
        ).structured_content
        arguments["data"].setdefault("expected_campaign_revision", campaign["revision"])
        arguments["data"].setdefault("idempotency_key", "create-actor")
    result = (await server.call_tool(name, arguments)).structured_content
    return result.get("result", result) if isinstance(result, dict) else result


def config(tmp_path: Path) -> McpConfig:
    return McpConfig(
        home=tmp_path / "home",
        database_url=None,
        coc_skills_dir=tmp_path / "missing-skills",
        modulegen_skills_dir=tmp_path / "missing-modulegen",
        npc_host_token="host-test-token",
    )


async def campaign_and_actor(server):
    campaign = await call(
        server,
        "campaign_change",
        {"action": "create", "data": {"name": "The Ashen Tide", "idempotency_key": "c"}},
    )
    actor = await call(
        server,
        "character_change",
        {
            "action": "create",
            "campaign_id": campaign["id"],
            "data": {"name": "Dr Hale", "sheet": {"pow": 65}},
        },
    )
    await call(
        server,
        "campaign_change",
        {
            "action": "grant_campaign",
            "campaign_id": campaign["id"],
            "data": {"target_principal_id": "player:hale", "role": "player"},
        },
    )
    await call(
        server,
        "campaign_change",
        {
            "action": "grant_actor",
            "campaign_id": campaign["id"],
            "data": {"target_principal_id": "player:hale", "actor_id": actor["id"]},
        },
    )
    return campaign, actor


def runtime_design(
    *,
    module_key: str,
    classification: str,
    root_module_key: str,
    parent_module_key: str,
    generation: int,
    scene_ids: list[str],
    prior_scene_id: str = "",
) -> dict:
    clue_id = f"clue:{module_key}"
    return {
        "schema_version": 2,
        "module_key": module_key,
        "classification": classification,
        "lineage": {
            "root_module_key": root_module_key,
            "parent_module_key": parent_module_key,
            "generation": generation,
        },
        "entities": [],
        "secrets": [],
        "clues": [
            {
                "id": clue_id,
                "label": "Salt-stained ledger",
                "trigger": "An investigator searches the records.",
                "revelation": "The missing ship visited an unknown inlet.",
                "linked_thread_ids": ["thread:missing-ship"],
                "fallback_scene_ids": [scene_ids[-1]],
            }
        ],
        "plot_nodes": [],
        "foreshadowing": [],
        "branches": [],
        "fronts": [
            {
                "id": "front:tide-cult",
                "name": "The Tide Cult",
                "goal": "Complete the moon-tide rite.",
                "stakes": "The harbor becomes a Mythos threshold.",
                "grim_portents": ["Fish wash ashore with human teeth."],
                "linked_thread_ids": ["thread:missing-ship"],
            }
        ],
        "story_threads": [
            {
                "id": "thread:missing-ship",
                "title": "The missing ship",
                "question": "Where did the Resolute vanish?",
                "linked_front_ids": ["front:tide-cult"],
                "linked_clue_ids": [clue_id],
            }
        ],
        "character_arcs": [
            {
                "id": "arc:hale-truth",
                "actor_id": "investigator:hale",
                "actor_kind": "pc",
                "opportunities": [
                    {
                        "id": f"opportunity:{module_key}",
                        "prompt": "Choose how far to pursue a destabilizing truth.",
                        "scene_ids": [scene_ids[-1]],
                        "thread_ids": ["thread:missing-ship"],
                    }
                ],
                "planned_beats": [],
                "possible_endings": [],
            }
        ],
        "scene_links": (
            []
            if not prior_scene_id
            else [
                {
                    "id": f"link:{module_key}",
                    "from_scene_id": prior_scene_id,
                    "to_scene_id": scene_ids[-1],
                    "kind": "investigator_choice",
                    "trigger": "The investigators follow evidence outside the current Atlas.",
                }
            ]
        ),
    }


async def install_runtime_pack(
    server,
    campaign_id: str,
    *,
    module_key: str,
    classification: str,
    root_module_key: str,
    parent_module_key: str = "",
    generation: int = 0,
    prior_scene_id: str = "",
    source_key: str | None = None,
    version: str = "1.0.0",
    activate: bool = True,
) -> tuple[str, list[str]]:
    source_key = source_key or f"{module_key}.md"
    operation_key = f"{module_key}-{version}".replace(".", "-")
    draft = await call(
        server,
        "module_draft",
        {
            "action": "start",
            "campaign_id": campaign_id,
            "data": {
                "name": source_key,
                "source_key": source_key,
                "title": module_key,
                "content": (
                    f"# {module_key}\n\n## Investigation\n"
                    f"Evidence waits here in Pack version {version}."
                ),
            },
            "idempotency_key": f"draft-{operation_key}",
        },
    )
    indexed = await call(
        server,
        "module_query",
        {"action": "index", "campaign_id": campaign_id, "data": {"module_id": draft["module_id"]}},
    )
    scene_ids = [str(item["stable_key"]) for item in indexed["scenes"]]
    evidence = await call(
        server,
        "module_draft",
        {"action": "evidence", "campaign_id": campaign_id, "data": {"job_id": draft["job_id"]}},
    )
    receipt = evidence["evidence"][0]["source_ref"]
    design = runtime_design(
        module_key=module_key,
        classification=classification,
        root_module_key=root_module_key,
        parent_module_key=parent_module_key,
        generation=generation,
        scene_ids=scene_ids,
        prior_scene_id=prior_scene_id,
    )
    decisions = {
        "manifest": {
            "title": module_key,
            "classification": "scenario",
            "compatibility": {"editions": ["7e"], "required_capabilities": ["module_pack_v2"]},
            "play_profile": {
                "investigator_count": {"minimum": 1, "maximum": 4, "source_refs": [receipt]},
                "ruleset": {
                    "supported": ["classic"],
                    "recommended": "classic",
                    "source_refs": [receipt],
                },
                "era": {"value": "1920s", "source_refs": [receipt]},
                "estimated_sessions": {"minimum": 1, "maximum": 1, "source_refs": [receipt]},
                "pregenerated_characters": {
                    "available": False,
                    "applicability": "None",
                    "source_refs": [receipt],
                },
                "solo_play": {"supported": False, "source_refs": [receipt]},
            },
            "continuity": {
                "series_id": None,
                "order": None,
                "continues_from": None,
                "state_policy": {},
            },
            "activation": {"mode": "campaign_attach", "default_active": False},
        },
        "catalogs": {
            name: []
            for name in (
                "clues",
                "handouts",
                "encounters",
                "hazards",
                "tomes",
                "spells",
                "mechanics",
            )
        },
        "narrative": {
            "dossiers": [],
            "endings": (
                [{"id": f"ending:{module_key}", "trigger": "Resolve the investigation."}]
                if classification == "authored_scenario"
                else []
            ),
        },
        "metadata": {"license": "private", "attribution": "Synthetic runtime test"},
        "version": version,
        "runtime_design": design,
    }
    edited = await call(
        server,
        "module_draft",
        {
            "action": "edit",
            "campaign_id": campaign_id,
            "data": {"job_id": draft["job_id"], "operation": "package", **decisions},
            "expected_revision": draft["job"]["revision"],
            "idempotency_key": f"edit-{operation_key}",
        },
    )
    finalized = await call(
        server,
        "module_draft",
        {
            "action": "finalize",
            "campaign_id": campaign_id,
            "data": {
                "job_id": draft["job_id"],
                "package_id": f"coc7e.module.{module_key}",
                "confirmation": {"confirmed": True, "note": "Reviewed runtime shard."},
            },
            "expected_revision": edited["job"]["revision"],
            "idempotency_key": f"finalize-{operation_key}",
        },
    )
    revision = (
        await call(server, "campaign_query", {"action": "get", "campaign_id": campaign_id})
    )["revision"]
    imported = await call(
        server,
        "content_pack",
        {
            "action": "import",
            "campaign_id": campaign_id,
            "data": {"artifact": finalized["artifact"]},
            "expected_revision": revision,
            "idempotency_key": f"import-{operation_key}",
        },
    )
    if activate:
        await call(
            server,
            "content_pack",
            {
                "action": "activate",
                "campaign_id": campaign_id,
                "data": {"module_id": imported["module_id"]},
                "expected_revision": revision,
                "idempotency_key": f"activate-{operation_key}",
            },
        )
    return imported["module_id"], scene_ids


def test_four_track_selector_prioritizes_exact_refs_without_deciding_intent() -> None:
    selected = select_actor_memory_context(
        actor_state={
            "id": "dr-hale",
            "name": "Dr Hale",
            "facts": [
                {
                    "id": "goal-1",
                    "kind": "actor_state",
                    "predicate": "obsession",
                    "content": "Prove the marsh lights have a rational origin.",
                    "importance": 5,
                }
            ],
        },
        actor_knowledge=[
            {
                "id": "knowledge-1",
                "revision_id": "r1",
                "actor_id": "dr-hale",
                "knowledge_key": "brass-key",
                "proposition": "The brass key opens the observatory archive.",
                "confidence": 5,
            }
        ],
        events=[
            {
                "id": "event-distractor",
                "summary": "A recent, dramatic discovery in the observatory.",
                "sequence": 999,
                "importance": 5,
                "payload": {"scene_id": "scene:observatory"},
            },
            {
                "id": "event-1",
                "summary": "Dr Hale found the brass key in the drowned chapel.",
                "sequence": 1,
                "payload": {"scene_id": "scene:chapel"},
            },
        ],
        current_refs=["scene:chapel"],
        query="brass key",
        budget_chars=8_000,
    )
    assert selected["identity"]
    assert selected["motivational"][0]["content"].startswith("Prove")
    assert selected["semantic"][0]["basis_ref"].startswith("knowledge:")
    assert selected["episodic"][0]["basis_ref"] == "event:event-1"
    assert selected["episodic"][0]["refs"] == ["scene:chapel"]
    assert "scene:scene:chapel" not in selected["episodic"][0]["refs"]
    assert selected["episodic"][0]["score"] > selected["episodic"][1]["score"]
    assert "intent" not in selected


def test_actor_memory_recalls_old_branch_history_without_keeper_disclosure_leak(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        server = create_server(config(tmp_path))
        campaign, actor = await campaign_and_actor(server)
        campaign_id = campaign["id"]
        for key, predicate, scope, content in (
            ("hale-public-fear", "phobia", "public", "Dr Hale fears deep open water."),
            (
                "hale-keeper-obsession",
                "obsession",
                "dm",
                "Dr Hale secretly wants to use the astrolabe.",
            ),
        ):
            await call(
                server,
                "memory_change",
                {
                    "action": "add",
                    "campaign_id": campaign_id,
                    "data": {
                        "fact_key": key,
                        "kind": "actor_state",
                        "subject_ref": f"actor:{actor['id']}",
                        "predicate": predicate,
                        "content": content,
                        "disclosure_scope": scope,
                    },
                    "idempotency_key": key,
                },
            )
        old = await call(
            server,
            "campaign_event",
            {
                "action": "add",
                "campaign_id": campaign_id,
                "data": {
                    "summary": "Dr Hale hides a brass astrolabe beneath the chapel floor.",
                    "event_type": "discovery",
                    "audience_scope": "actor",
                    "participants": [{"actor_id": actor["id"], "role": "witness"}],
                },
                "idempotency_key": "old-astrolabe",
            },
        )
        keeper_only = await call(
            server,
            "campaign_event",
            {
                "action": "add",
                "campaign_id": campaign_id,
                "data": {
                    "summary": "Keeper cipher: the astrolabe points to the cult's sanctuary.",
                    "event_type": "keeper_note",
                    "audience_scope": "dm",
                    "participants": [{"actor_id": actor["id"], "role": "target"}],
                },
                "idempotency_key": "keeper-cipher",
            },
        )
        for index in range(205):
            await call(
                server,
                "campaign_event",
                {
                    "action": "add",
                    "campaign_id": campaign_id,
                    "data": {
                        "summary": f"Routine interview note {index}.",
                        "audience_scope": "public",
                        "participants": [{"actor_id": actor["id"], "role": "witness"}],
                    },
                    "idempotency_key": f"filler-{index}",
                },
            )
        player = await call(
            server,
            "continuity_context",
            {
                "campaign_id": campaign_id,
                "actor_id": actor["id"],
                "purpose": "actor_memory",
                "query": "brass astrolabe chapel",
                "principal_id": "player:hale",
            },
        )
        player_ids = {item["record"]["id"] for item in player["memory"]["episodic"]}
        player_state = {
            item["content"]
            for track in ("identity", "motivational")
            for item in player["memory"][track]
        }
        assert old["id"] in player_ids
        assert keeper_only["id"] not in player_ids
        assert "Dr Hale fears deep open water." in player_state
        assert "Dr Hale secretly wants to use the astrolabe." not in player_state
        keeper = await call(
            server,
            "continuity_context",
            {
                "campaign_id": campaign_id,
                "actor_id": actor["id"],
                "purpose": "actor_memory",
                "query": "keeper cipher sanctuary",
            },
        )
        assert keeper_only["id"] in {item["record"]["id"] for item in keeper["memory"]["episodic"]}
        assert "Dr Hale secretly wants to use the astrolabe." in {
            item["content"]
            for track in ("identity", "motivational")
            for item in keeper["memory"][track]
        }

        branch = await call(
            server, "branch_query", {"action": "current", "campaign_id": campaign_id}
        )
        current_campaign = await call(
            server, "campaign_query", {"action": "get", "campaign_id": campaign_id}
        )
        snapshot = await call(
            server,
            "snapshot_change",
            {
                "action": "create",
                "campaign_id": campaign_id,
                "data": {"label": "Before the red moon", "expected_head_snapshot_id": ""},
                "expected_revision": current_campaign["revision"],
                "expected_branch_id": branch["branch"]["id"],
                "idempotency_key": "snapshot-before-red-moon",
            },
        )
        current_campaign = await call(
            server, "campaign_query", {"action": "get", "campaign_id": campaign_id}
        )
        await call(
            server,
            "branch_change",
            {
                "action": "create",
                "campaign_id": campaign_id,
                "data": {
                    "name": "Red moon timeline",
                    "from_snapshot_id": snapshot["id"],
                    "checkout": True,
                },
                "expected_revision": current_campaign["revision"],
                "expected_branch_id": branch["branch"]["id"],
                "idempotency_key": "red-moon-branch",
            },
        )
        branch_event = await call(
            server,
            "campaign_event",
            {
                "action": "add",
                "campaign_id": campaign_id,
                "data": {
                    "summary": "The red moon rises over the marsh.",
                    "audience_scope": "actor",
                    "participants": [{"actor_id": actor["id"], "role": "witness"}],
                },
                "idempotency_key": "red-moon-event",
            },
        )
        original = await call(
            server,
            "continuity_context",
            {
                "campaign_id": campaign_id,
                "actor_id": actor["id"],
                "purpose": "actor_memory",
                "query": "red moon marsh",
                "branch_id": branch["branch"]["id"],
            },
        )
        assert branch_event["id"] not in {
            item["record"]["id"] for item in original["memory"]["episodic"]
        }

    asyncio.run(exercise())


def test_actor_knowledge_list_and_search_filter_disclosure_at_query_entry(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        server = create_server(config(tmp_path))
        campaign, actor = await campaign_and_actor(server)
        for key, scope in (
            ("private-cult-name", "dm"),
            ("owned-chapel-mark", "owner"),
            ("shared-tide-warning", "party"),
        ):
            await call(
                server,
                "actor_knowledge_change",
                {
                    "action": "add",
                    "campaign_id": campaign["id"],
                    "actor_id": actor["id"],
                    "data": {
                        "knowledge_key": key,
                        "proposition": f"Evidence concerning {key}.",
                        "disclosure_scope": scope,
                    },
                    "idempotency_key": key,
                },
            )
        common = {
            "campaign_id": campaign["id"],
            "actor_id": actor["id"],
            "principal_id": "player:hale",
        }
        listed = await call(server, "actor_knowledge_query", {"action": "list", **common})
        searched = await call(
            server,
            "actor_knowledge_query",
            {"action": "search", **common, "data": {"query": "evidence cult chapel"}},
        )
        expected = {"owned-chapel-mark", "shared-tide-warning"}
        assert {item["knowledge_key"] for item in listed["knowledge"]} == expected
        assert {item["knowledge_key"] for item in searched["knowledge"]} == expected

    asyncio.run(exercise())


def test_campaign_expansion_is_keeper_only_lobby_review_and_never_writes_state(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        server = create_server(config(tmp_path))
        campaign, _actor = await campaign_and_actor(server)
        campaign_id = campaign["id"]
        seed_module_id, seed_scenes = await install_runtime_pack(
            server,
            campaign_id,
            module_key="ashen-seed",
            classification="emergent_seed",
            root_module_key="ashen-seed",
        )
        player_before = await call(
            server,
            "campaign_query",
            {
                "action": "get",
                "campaign_id": campaign_id,
                "principal_id": "player:hale",
            },
        )
        assert player_before["id"] == campaign_id
        current = await call(
            server, "campaign_query", {"action": "get", "campaign_id": campaign_id}
        )
        manifest = new_playthrough_manifest(
            campaign_line_id="ashen-tide",
            module_ids=[seed_module_id],
            campaign_mode="emergent",
            content_lineage=[
                {
                    "module_id": seed_module_id,
                    "classification": "emergent_seed",
                    "root_module_id": seed_module_id,
                    "parent_module_id": "",
                    "generation": 0,
                    "scene_ids": seed_scenes,
                    "source_refs": [],
                }
            ],
        )
        initialized = await call(
            server,
            "playthrough_manifest",
            {
                "action": "initialize",
                "campaign_id": campaign_id,
                "manifest": manifest,
                "expected_revision": current["revision"],
                "idempotency_key": "manifest",
            },
        )
        before = await call(server, "campaign_query", {"action": "get", "campaign_id": campaign_id})
        bundle = await call(
            server,
            "continuity_context",
            {
                "campaign_id": campaign_id,
                "purpose": "campaign_expansion",
                "query": "Follow the investigators to a plausible inlet outside the Atlas.",
            },
        )
        design_ref = bundle["context"]["campaign_design"]["basis_ref"]
        assert bundle["delegation"]["tools_exposed"] is False
        assert bundle["constraints"]["may_write_state"] is False
        validated = await call(
            server,
            "bounded_evaluation",
            {
                "action": "validate",
                "campaign_id": campaign_id,
                "bundle_receipt": bundle["bundle_receipt"],
                "proposal": {
                    "schema_version": 1,
                    "bundle_id": bundle["bundle_id"],
                    "purpose": "campaign_expansion",
                    "campaign_line_id": "ashen-tide",
                    "title": "The uncharted inlet",
                    "source_markdown": (
                        "<!-- sagasmith-runtime-manifest\n"
                        '{"schema_version":2,"module_key":"inlet-episode"}\n-->'
                    ),
                    "generation_basis_refs": [design_ref],
                    "claims": [],
                    "unresolved": [],
                    "requires_keeper_review": True,
                    "decision_summary": "Review before authoring and activation.",
                },
            },
        )
        assert validated["authoritative_state_changed"] is False
        after = await call(server, "campaign_query", {"action": "get", "campaign_id": campaign_id})
        assert after["revision"] == before["revision"]
        assert initialized["manifest"]["campaign_mode"] == "emergent"
        player_after = await call(
            server,
            "campaign_query",
            {
                "action": "get",
                "campaign_id": campaign_id,
                "principal_id": "player:hale",
            },
        )
        assert player_after["id"] == campaign_id
        with pytest.raises(Exception, match="only to the Keeper"):
            await call(
                server,
                "continuity_context",
                {
                    "campaign_id": campaign_id,
                    "purpose": "campaign_expansion",
                    "query": "Player tries to generate truth.",
                    "principal_id": "player:hale",
                },
            )

    asyncio.run(exercise())


def test_three_chapter_playthrough_manifest_restores_at_branch_boundary(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = create_server(config(tmp_path))
        campaign, _actor = await campaign_and_actor(server)
        campaign_id = campaign["id"]
        seed_module_id, seed_scenes = await install_runtime_pack(
            server,
            campaign_id,
            module_key="seed",
            classification="emergent_seed",
            root_module_key="seed",
        )
        episode_one_module_id, episode_one_scenes = await install_runtime_pack(
            server,
            campaign_id,
            module_key="episode-1",
            classification="emergent_episode",
            root_module_key="seed",
            parent_module_key="seed",
            generation=1,
            prior_scene_id=seed_scenes[-1],
        )
        episode_two_module_id, episode_two_scenes = await install_runtime_pack(
            server,
            campaign_id,
            module_key="episode-2",
            classification="emergent_episode",
            root_module_key="seed",
            parent_module_key="episode-1",
            generation=2,
            prior_scene_id=episode_one_scenes[-1],
        )
        seed = new_playthrough_manifest(
            campaign_line_id="ashen-tide",
            module_ids=[seed_module_id],
            campaign_mode="emergent",
            content_lineage=[
                {
                    "module_id": seed_module_id,
                    "classification": "emergent_seed",
                    "root_module_id": seed_module_id,
                    "parent_module_id": "",
                    "generation": 0,
                    "scene_ids": seed_scenes,
                    "source_refs": [],
                }
            ],
        )
        current = await call(
            server, "campaign_query", {"action": "get", "campaign_id": campaign_id}
        )
        await call(
            server,
            "playthrough_manifest",
            {
                "action": "initialize",
                "campaign_id": campaign_id,
                "manifest": seed,
                "expected_revision": current["revision"],
                "idempotency_key": "seed",
            },
        )
        episode_one = {**seed, "module_ids": [seed_module_id, episode_one_module_id]}
        episode_one["content_lineage"] = [
            *seed["content_lineage"],
            {
                "module_id": episode_one_module_id,
                "classification": "emergent_episode",
                "root_module_id": seed_module_id,
                "parent_module_id": seed_module_id,
                "generation": 1,
                "scene_ids": episode_one_scenes,
                "source_refs": [],
            },
        ]
        current = await call(
            server, "campaign_query", {"action": "get", "campaign_id": campaign_id}
        )
        await call(
            server,
            "playthrough_manifest",
            {
                "action": "replace",
                "campaign_id": campaign_id,
                "manifest": episode_one,
                "expected_revision": current["revision"],
                "idempotency_key": "episode-one",
            },
        )
        branch = await call(
            server, "branch_query", {"action": "current", "campaign_id": campaign_id}
        )
        current = await call(
            server, "campaign_query", {"action": "get", "campaign_id": campaign_id}
        )
        checkpoint = await call(
            server,
            "snapshot_change",
            {
                "action": "create",
                "campaign_id": campaign_id,
                "data": {"label": "After episode one", "expected_head_snapshot_id": ""},
                "expected_revision": current["revision"],
                "expected_branch_id": branch["branch"]["id"],
                "idempotency_key": "episode-one-checkpoint",
            },
        )
        episode_two = {
            **episode_one,
            "module_ids": [seed_module_id, episode_one_module_id, episode_two_module_id],
        }
        episode_two["content_lineage"] = [
            *episode_one["content_lineage"],
            {
                "module_id": episode_two_module_id,
                "classification": "emergent_episode",
                "root_module_id": seed_module_id,
                "parent_module_id": episode_one_module_id,
                "generation": 2,
                "scene_ids": episode_two_scenes,
                "source_refs": [],
            },
        ]
        current = await call(
            server, "campaign_query", {"action": "get", "campaign_id": campaign_id}
        )
        await call(
            server,
            "playthrough_manifest",
            {
                "action": "replace",
                "campaign_id": campaign_id,
                "manifest": episode_two,
                "expected_revision": current["revision"],
                "idempotency_key": "episode-two",
            },
        )
        current_line = await call(
            server,
            "playthrough_manifest",
            {"action": "get", "campaign_id": campaign_id},
        )
        assert current_line["manifest"]["module_ids"] == [
            seed_module_id,
            episode_one_module_id,
            episode_two_module_id,
        ]
        current = await call(
            server, "campaign_query", {"action": "get", "campaign_id": campaign_id}
        )
        await call(
            server,
            "snapshot_change",
            {
                "action": "create",
                "campaign_id": campaign_id,
                "data": {
                    "label": "After episode two",
                    "expected_head_snapshot_id": checkpoint["id"],
                },
                "expected_revision": current["revision"],
                "expected_branch_id": branch["branch"]["id"],
                "idempotency_key": "episode-two-checkpoint",
            },
        )
        current = await call(
            server, "campaign_query", {"action": "get", "campaign_id": campaign_id}
        )
        await call(
            server,
            "branch_change",
            {
                "action": "create",
                "campaign_id": campaign_id,
                "data": {
                    "name": "Episode one alternative",
                    "from_snapshot_id": checkpoint["id"],
                    "checkout": True,
                },
                "expected_revision": current["revision"],
                "expected_branch_id": branch["branch"]["id"],
                "idempotency_key": "episode-one-alternative",
            },
        )
        restored = await call(
            server,
            "playthrough_manifest",
            {"action": "get", "campaign_id": campaign_id},
        )
        assert restored["manifest"]["module_ids"] == [
            seed_module_id,
            episode_one_module_id,
        ]

    asyncio.run(exercise())


def test_playthrough_manifest_rejects_unattested_inactive_and_wrong_runtime_packs(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        server = create_server(config(tmp_path))
        campaign, _actor = await campaign_and_actor(server)
        campaign_id = campaign["id"]
        module_id, scene_ids = await install_runtime_pack(
            server,
            campaign_id,
            module_key="attested-seed",
            classification="emergent_seed",
            root_module_key="attested-seed",
        )

        def seed_manifest(
            *, target_module: str = module_id, scenes=None, classification="emergent_seed"
        ):
            return new_playthrough_manifest(
                campaign_line_id="attested-line",
                module_ids=[target_module],
                campaign_mode=(
                    "emergent" if classification == "emergent_seed" else "authored_scenario"
                ),
                content_lineage=[
                    {
                        "module_id": target_module,
                        "classification": classification,
                        "root_module_id": target_module,
                        "parent_module_id": "",
                        "generation": 0,
                        "scene_ids": list(scene_ids if scenes is None else scenes),
                        "source_refs": [],
                    }
                ],
            )

        revision = (
            await call(server, "campaign_query", {"action": "get", "campaign_id": campaign_id})
        )["revision"]
        with pytest.raises(Exception, match="exactly match its Scene Atlas"):
            await call(
                server,
                "playthrough_manifest",
                {
                    "action": "initialize",
                    "campaign_id": campaign_id,
                    "manifest": seed_manifest(scenes=["scene:forged"]),
                    "expected_revision": revision,
                    "idempotency_key": "wrong-atlas",
                },
            )
        with pytest.raises(Exception, match="does not match runtime_design"):
            await call(
                server,
                "playthrough_manifest",
                {
                    "action": "initialize",
                    "campaign_id": campaign_id,
                    "manifest": seed_manifest(classification="authored_scenario"),
                    "expected_revision": revision,
                    "idempotency_key": "wrong-runtime",
                },
            )
        other = await call(
            server,
            "campaign_change",
            {"action": "create", "data": {"name": "Other case", "idempotency_key": "other"}},
        )
        with pytest.raises(Exception, match="not imported into this campaign"):
            await call(
                server,
                "playthrough_manifest",
                {
                    "action": "initialize",
                    "campaign_id": other["id"],
                    "manifest": seed_manifest(),
                    "expected_revision": other["revision"],
                    "idempotency_key": "other-campaign-pack",
                },
            )
        await call(
            server,
            "content_pack",
            {
                "action": "deactivate",
                "campaign_id": campaign_id,
                "data": {"module_id": module_id},
                "expected_revision": revision,
                "idempotency_key": "deactivate-attested-seed",
            },
        )
        with pytest.raises(Exception, match="is not active"):
            await call(
                server,
                "playthrough_manifest",
                {
                    "action": "initialize",
                    "campaign_id": campaign_id,
                    "manifest": seed_manifest(),
                    "expected_revision": revision,
                    "idempotency_key": "inactive-pack",
                },
            )

    asyncio.run(exercise())


def test_authored_scenario_can_append_reviewed_off_atlas_episode_without_rewriting_root(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        server = create_server(config(tmp_path))
        campaign, _actor = await campaign_and_actor(server)
        campaign_id = campaign["id"]
        root_id, root_scenes = await install_runtime_pack(
            server,
            campaign_id,
            module_key="published-case",
            classification="authored_scenario",
            root_module_key="published-case",
        )
        extension_id, extension_scenes = await install_runtime_pack(
            server,
            campaign_id,
            module_key="windmill-detour",
            classification="emergent_episode",
            root_module_key="published-case",
            parent_module_key="published-case",
            generation=1,
            prior_scene_id=root_scenes[-1],
        )
        root_lineage = {
            "module_id": root_id,
            "classification": "authored_scenario",
            "root_module_id": root_id,
            "parent_module_id": "",
            "generation": 0,
            "scene_ids": root_scenes,
            "source_refs": [],
        }
        original_root = dict(root_lineage)
        initial = new_playthrough_manifest(
            campaign_line_id="published-line",
            module_ids=[root_id],
            content_lineage=[root_lineage],
        )
        revision = (
            await call(server, "campaign_query", {"action": "get", "campaign_id": campaign_id})
        )["revision"]
        await call(
            server,
            "playthrough_manifest",
            {
                "action": "initialize",
                "campaign_id": campaign_id,
                "manifest": initial,
                "expected_revision": revision,
                "idempotency_key": "published-initial",
            },
        )
        extension = {
            **initial,
            "campaign_mode": "authored_with_extensions",
            "module_ids": [root_id, extension_id],
            "content_lineage": [
                initial["content_lineage"][0],
                {
                    "module_id": extension_id,
                    "classification": "emergent_episode",
                    "root_module_id": root_id,
                    "parent_module_id": root_id,
                    "generation": 1,
                    "scene_ids": extension_scenes,
                    "source_refs": [],
                },
            ],
        }
        revision = (
            await call(server, "campaign_query", {"action": "get", "campaign_id": campaign_id})
        )["revision"]
        replaced = await call(
            server,
            "playthrough_manifest",
            {
                "action": "replace",
                "campaign_id": campaign_id,
                "manifest": extension,
                "expected_revision": revision,
                "idempotency_key": "published-extension",
            },
        )
        assert replaced["manifest"]["campaign_mode"] == "authored_with_extensions"
        assert replaced["manifest"]["content_lineage"][0] == original_root

    asyncio.run(exercise())


def test_playthrough_references_block_pack_deactivate_remove_and_replacement_activation(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        server = create_server(config(tmp_path))
        campaign, _actor = await campaign_and_actor(server)
        campaign_id = campaign["id"]
        old_id, old_scenes = await install_runtime_pack(
            server,
            campaign_id,
            module_key="lifecycle-case",
            classification="authored_scenario",
            root_module_key="lifecycle-case",
            source_key="lifecycle-case.md",
            version="1.0.0",
        )
        manifest = new_playthrough_manifest(
            campaign_line_id="lifecycle-line",
            module_ids=[old_id],
            content_lineage=[
                {
                    "module_id": old_id,
                    "classification": "authored_scenario",
                    "root_module_id": old_id,
                    "parent_module_id": "",
                    "generation": 0,
                    "scene_ids": old_scenes,
                    "source_refs": [],
                }
            ],
        )
        revision = (
            await call(server, "campaign_query", {"action": "get", "campaign_id": campaign_id})
        )["revision"]
        await call(
            server,
            "playthrough_manifest",
            {
                "action": "initialize",
                "campaign_id": campaign_id,
                "manifest": manifest,
                "expected_revision": revision,
                "idempotency_key": "lifecycle-manifest",
            },
        )
        revision = (
            await call(server, "campaign_query", {"action": "get", "campaign_id": campaign_id})
        )["revision"]
        for action in ("deactivate", "remove"):
            with pytest.raises(Exception, match="referenced by a playthrough manifest"):
                await call(
                    server,
                    "content_pack",
                    {
                        "action": action,
                        "campaign_id": campaign_id,
                        "data": {"module_id": old_id},
                        "expected_revision": revision,
                        "idempotency_key": f"blocked-{action}",
                    },
                )
        assert (
            await call(
                server,
                "playthrough_manifest",
                {"action": "get", "campaign_id": campaign_id},
            )
        )["manifest"] == manifest

        new_id, _new_scenes = await install_runtime_pack(
            server,
            campaign_id,
            module_key="lifecycle-case",
            classification="authored_scenario",
            root_module_key="lifecycle-case",
            source_key="lifecycle-case.md",
            version="2.0.0",
            activate=False,
        )
        revision = (
            await call(server, "campaign_query", {"action": "get", "campaign_id": campaign_id})
        )["revision"]
        with pytest.raises(Exception, match="referenced by a playthrough manifest"):
            await call(
                server,
                "content_pack",
                {
                    "action": "activate",
                    "campaign_id": campaign_id,
                    "data": {"module_id": new_id},
                    "expected_revision": revision,
                    "idempotency_key": "blocked-replacement",
                },
            )
        packs = await call(
            server,
            "content_pack",
            {"action": "list", "campaign_id": campaign_id},
        )
        states = {str(item["id"]): item["active"] for item in packs["packs"]}
        assert states[old_id] is True
        assert states[new_id] is False
        assert (
            await call(
                server,
                "playthrough_manifest",
                {"action": "get", "campaign_id": campaign_id},
            )
        )["manifest"] == manifest

    asyncio.run(exercise())


def test_npc_v5_requires_explicit_grounding_modes() -> None:
    base = {
        "schema_version": 5,
        "conversation_id": "conversation",
        "activation_id": "activation",
        "actor_runtime_id": "runtime",
        "response_bid": {"should_respond": True, "urgency": 10, "reason": "asked"},
        "private_intent": "",
        "utterance_segments": [
            {
                "text": "The ledger was altered.",
                "content_mode": "grounded",
                "basis_refs": ["knowledge:k:r"],
                "targets": [],
                "speech_act": "answer",
                "truth_posture": "supported",
                "language": "English",
                "delivery": "quiet",
            }
        ],
        "proposed_action": {"summary": "", "target_refs": [], "settlement": "narrative"},
        "resolution_requests": [],
        "working_deltas": {"facts": [], "actor_knowledge": [], "commitments": []},
        "visible_cues": [],
        "decision_summary": "",
    }
    assert (
        normalize_conversation_proposal(base)["utterance_segments"][0]["content_mode"] == "grounded"
    )
    invalid = {**base, "utterance_segments": [{**base["utterance_segments"][0], "basis_refs": []}]}
    with pytest.raises(ValueError, match="actor-owned basis_refs"):
        normalize_conversation_proposal(invalid)
