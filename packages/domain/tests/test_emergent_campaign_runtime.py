from __future__ import annotations

import copy
import json

import pytest
from sagasmith_core.modules import MarkdownModuleParser

from sagasmith_coc.module_profile import CocModuleProfile, runtime_manifest_errors
from sagasmith_coc.playthrough import (
    new_playthrough_manifest,
    validate_playthrough_manifest,
    validate_playthrough_transition,
)


def lineage(module_id, classification, root, parent="", generation=0, scenes=()):
    return {
        "module_id": module_id,
        "classification": classification,
        "root_module_id": root,
        "parent_module_id": parent,
        "generation": generation,
        "scene_ids": list(scenes),
        "source_refs": [],
    }


def runtime(classification="emergent_seed", parent="", generation=0):
    module_key = "arkham-seed" if generation == 0 else f"arkham-episode-{generation}"
    root = "arkham-seed"
    scene = "scene:arkham" if generation == 0 else f"scene:chapter-{generation}"
    manifest = {
        "schema_version": 2,
        "module_key": module_key,
        "classification": classification,
        "lineage": {
            "root_module_key": root,
            "parent_module_key": parent,
            "generation": generation,
        },
        "entities": [],
        "secrets": [],
        "clues": [
            {
                "id": f"clue:chapter-{generation}",
                "label": "A salt-stained shipping ledger",
                "trigger": "An investigator searches the records room.",
                "revelation": "A missing ship called at an uncharted inlet.",
                "linked_thread_ids": ["thread:missing-ship"],
                "fallback_scene_ids": [scene],
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
                "stakes": "Arkham's harbor becomes a Mythos threshold.",
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
                "linked_clue_ids": [f"clue:chapter-{generation}"],
            }
        ],
        "character_arcs": [
            {
                "id": "arc:dr-hale-obsession",
                "actor_id": "pc:dr-hale",
                "actor_kind": "pc",
                "opportunities": [
                    {
                        "id": f"opportunity:truth-{generation}",
                        "prompt": "Choose how far to pursue a truth that threatens stability.",
                        "scene_ids": [scene],
                        "thread_ids": ["thread:missing-ship"],
                    }
                ],
                "planned_beats": [],
                "possible_endings": [],
            }
        ],
        "scene_links": (
            []
            if generation == 0
            else [
                {
                    "id": f"link:chapter-{generation}",
                    "from_scene_id": (
                        "scene:arkham" if generation == 1 else f"scene:chapter-{generation - 1}"
                    ),
                    "to_scene_id": scene,
                    "kind": "investigator_choice",
                    "trigger": "The investigators follow the ledger beyond the current Atlas.",
                }
            ]
        ),
    }
    text = (
        "<!-- sagasmith-runtime-manifest\n"
        + json.dumps(manifest)
        + f"\n-->\n# Chapter {generation}\n\n## {scene}\nEvidence waits.\n"
    )
    metadata = MarkdownModuleParser(profile=CocModuleProfile()).document_metadata(text)
    return metadata


def test_runtime_design_is_orthogonal_to_coc_scenario_classification() -> None:
    metadata = runtime()
    assert metadata["runtime_manifest_errors"] == []
    assert metadata["runtime_manifest"]["classification"] == "emergent_seed"
    assert "scenario" not in {
        "authored_scenario",
        "emergent_seed",
        "emergent_episode",
    }


def test_three_chapter_emergent_playthrough_keeps_threads_and_investigator_agency() -> None:
    assert runtime()["runtime_manifest_errors"] == []
    assert runtime("emergent_episode", "arkham-seed", 1)["runtime_manifest_errors"] == []
    assert runtime("emergent_episode", "arkham-episode-1", 2)["runtime_manifest_errors"] == []
    manifest = new_playthrough_manifest(
        campaign_line_id="arkham-tide",
        module_ids=["arkham-seed"],
        campaign_mode="emergent",
        content_lineage=[
            lineage("arkham-seed", "emergent_seed", "arkham-seed", scenes=("scene:arkham",))
        ],
    )
    for generation, parent in ((1, "arkham-seed"), (2, "arkham-episode-1")):
        module_id = f"arkham-episode-{generation}"
        manifest["module_ids"].append(module_id)
        manifest["content_lineage"].append(
            lineage(
                module_id,
                "emergent_episode",
                "arkham-seed",
                parent,
                generation,
                (f"scene:chapter-{generation}",),
            )
        )
        manifest["traversal"]["reachable_scene_ids"].append(f"scene:chapter-{generation}")
    manifest["traversal"]["reachable_scene_ids"].insert(0, "scene:arkham")
    manifest["traversal"]["visited_scene_ids"] = ["scene:arkham", "scene:chapter-1"]
    manifest["current"] = {
        "module_id": "arkham-episode-2",
        "chapter_id": "chapter-2",
        "chapter_title": "The uncharted inlet",
        "scene_id": "scene:chapter-2",
        "scene_title": "Moon-tide caves",
        "objective": "Find the Resolute.",
    }
    manifest["front_progress"] = [
        {
            "id": "front:tide-cult",
            "status": "advanced",
            "stage": 1,
            "source_ref": None,
            "evidence_refs": [{"kind": "event", "ref_id": "event:rite-begins"}],
        }
    ]
    manifest["thread_progress"] = [
        {
            "id": "thread:missing-ship",
            "status": "advanced",
            "source_ref": None,
            "evidence_refs": [{"kind": "clue", "ref_id": "clue:ledger"}],
        }
    ]
    manifest["arc_progress"] = [
        {
            "id": "arc:dr-hale-obsession",
            "actor_id": "pc:dr-hale",
            "actor_kind": "pc",
            "status": "available",
            "completed_opportunity_ids": [],
            "source_ref": None,
            "evidence_refs": [],
        }
    ]
    validated = validate_playthrough_manifest(manifest)
    assert [item["generation"] for item in validated["content_lineage"]] == [0, 1, 2]
    assert validated["arc_progress"][0]["completed_opportunity_ids"] == []


def test_authored_scenario_off_atlas_extension_preserves_the_root() -> None:
    root = lineage(
        "published-scenario",
        "authored_scenario",
        "published-scenario",
        scenes=("scene:manor",),
    )
    original = copy.deepcopy(root)
    manifest = new_playthrough_manifest(
        campaign_line_id="published-case",
        module_ids=["published-scenario"],
        content_lineage=[root],
    )
    manifest["campaign_mode"] = "authored_with_extensions"
    manifest["module_ids"].append("published-windmill-detour")
    manifest["content_lineage"].append(
        lineage(
            "published-windmill-detour",
            "emergent_episode",
            "published-scenario",
            "published-scenario",
            1,
            ("scene:windmill",),
        )
    )
    validated = validate_playthrough_manifest(manifest)
    assert validated["content_lineage"][0] == original


@pytest.mark.parametrize(
    "mutation, message",
    [
        (
            lambda value: value["content_lineage"][1].update(parent_module_id="missing"),
            "not installed",
        ),
        (lambda value: value["content_lineage"][1].update(generation=7), r"parent \+ 1"),
        (lambda value: value["content_lineage"][1].update(root_module_id="other"), "parent's root"),
        (
            lambda value: value["content_lineage"][1]["scene_ids"].append("scene:root"),
            "unique across shards",
        ),
    ],
)
def test_lineage_and_atlas_error_paths(mutation, message) -> None:
    manifest = new_playthrough_manifest(
        campaign_line_id="line",
        module_ids=["seed", "episode"],
        campaign_mode="emergent",
        content_lineage=[
            lineage("seed", "emergent_seed", "seed", scenes=("scene:root",)),
            lineage("episode", "emergent_episode", "seed", "seed", 1, ("scene:next",)),
        ],
    )
    mutation(manifest)
    with pytest.raises(ValueError, match=message):
        validate_playthrough_manifest(manifest)


def test_material_progress_requires_evidence() -> None:
    manifest = new_playthrough_manifest(
        campaign_line_id="line",
        module_ids=["seed"],
        campaign_mode="emergent",
        content_lineage=[lineage("seed", "emergent_seed", "seed")],
    )
    manifest["front_progress"] = [
        {
            "id": "front:cult",
            "status": "advanced",
            "stage": 1,
            "source_ref": None,
            "evidence_refs": [],
        }
    ]
    with pytest.raises(ValueError, match="requires evidence_refs"):
        validate_playthrough_manifest(manifest)


def test_runtime_rejects_predetermined_investigator_arc_and_episode_without_link() -> None:
    metadata = runtime("emergent_episode", "arkham-seed", 1)
    manifest = metadata["runtime_manifest"]
    manifest["character_arcs"][0]["planned_beats"] = ["Dr Hale accepts the truth."]
    manifest["scene_links"] = []
    text = "<!-- sagasmith-runtime-manifest\n" + json.dumps(manifest) + "\n-->\n# Episode"
    errors = MarkdownModuleParser(profile=CocModuleProfile()).document_metadata(text)[
        "runtime_manifest_errors"
    ]
    assert any("outcomes remain player choice" in error for error in errors)
    assert "emergent_episode runtime manifest requires at least one scene_link" in errors


def test_playthrough_transition_allows_progress_updates_and_reviewed_append() -> None:
    current = new_playthrough_manifest(
        campaign_line_id="published-case",
        module_ids=["published"],
        content_lineage=[
            lineage("published", "authored_scenario", "published", scenes=("scene:manor",))
        ],
    )
    successor = copy.deepcopy(current)
    successor["campaign_mode"] = "authored_with_extensions"
    successor["module_ids"].append("windmill")
    successor["content_lineage"].append(
        lineage(
            "windmill",
            "emergent_episode",
            "published",
            "published",
            1,
            ("scene:windmill",),
        )
    )
    successor["traversal"]["reachable_scene_ids"] = ["scene:manor", "scene:windmill"]
    successor["current"]["module_id"] = "windmill"
    successor["current"]["scene_id"] = "scene:windmill"
    assert validate_playthrough_transition(current, successor) == successor

    progressed = copy.deepcopy(successor)
    progressed["front_progress"] = [
        {
            "id": "front:tide",
            "status": "advanced",
            "stage": 1,
            "source_ref": None,
            "evidence_refs": [{"kind": "event", "ref_id": "event:tide"}],
        }
    ]
    assert validate_playthrough_transition(successor, progressed)["front_progress"]


@pytest.mark.parametrize(
    "mutation, message",
    [
        (
            lambda value: value.update(front_progress=[]),
            "front_progress may not delete",
        ),
        (
            lambda value: value["front_progress"][0].update(status="dormant"),
            "front_progress.*may not move",
        ),
        (
            lambda value: value["front_progress"][0].update(stage=1),
            "front_progress.*stage may not decrease",
        ),
        (
            lambda value: value.update(thread_progress=[]),
            "thread_progress may not delete",
        ),
        (
            lambda value: value["thread_progress"][0].update(status="open"),
            "thread_progress.*may not move",
        ),
        (
            lambda value: value["traversal"].update(visited_scene_ids=[]),
            "visited_scene_ids may not delete",
        ),
        (
            lambda value: value.update(arc_progress=[]),
            "arc_progress may not delete",
        ),
        (
            lambda value: value["arc_progress"][0].update(
                completed_opportunity_ids=[]
            ),
            "completed_opportunity_ids may not delete",
        ),
        (
            lambda value: value["arc_progress"][0].update(actor_id="other"),
            "actor identity is immutable",
        ),
        (
            lambda value: value["front_progress"][0].update(evidence_refs=[]),
            "requires evidence_refs",
        ),
    ],
)
def test_playthrough_transition_rejects_progress_history_loss(mutation, message) -> None:
    current = new_playthrough_manifest(
        campaign_line_id="line",
        module_ids=["seed"],
        campaign_mode="emergent",
        content_lineage=[lineage("seed", "emergent_seed", "seed", scenes=("scene:seed",))],
    )
    evidence = [{"kind": "event", "ref_id": "event:advance"}]
    current["traversal"] = {
        "reachable_scene_ids": ["scene:seed"],
        "visited_scene_ids": ["scene:seed"],
    }
    current["front_progress"] = [
        {
            "id": "front:tide",
            "status": "advanced",
            "stage": 2,
            "source_ref": None,
            "evidence_refs": evidence,
        }
    ]
    current["thread_progress"] = [
        {
            "id": "thread:ship",
            "status": "advanced",
            "source_ref": None,
            "evidence_refs": evidence,
        }
    ]
    current["arc_progress"] = [
        {
            "id": "arc:hale",
            "actor_id": "investigator:hale",
            "actor_kind": "pc",
            "status": "advanced",
            "completed_opportunity_ids": ["opportunity:choice"],
            "source_ref": None,
            "evidence_refs": evidence,
        }
    ]
    successor = copy.deepcopy(current)
    mutation(successor)
    with pytest.raises(ValueError, match=message):
        validate_playthrough_transition(current, successor)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda value: value.update(campaign_line_id="other"), "campaign_line_id"),
        (lambda value: value.update(module_ids=[]), "must not be empty"),
        (
            lambda value: value["content_lineage"][0].update(scene_ids=["scene:changed"]),
            "lineage and shard metadata",
        ),
        (
            lambda value: value["content_lineage"][0].update(root_module_id="changed"),
            "root shards",
        ),
    ],
)
def test_playthrough_transition_rejects_identity_and_lineage_rewrites(mutation, message) -> None:
    current = new_playthrough_manifest(
        campaign_line_id="line",
        module_ids=["seed"],
        campaign_mode="emergent",
        content_lineage=[lineage("seed", "emergent_seed", "seed", scenes=("scene:seed",))],
    )
    successor = copy.deepcopy(current)
    mutation(successor)
    with pytest.raises(ValueError, match=message):
        validate_playthrough_transition(current, successor)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (
            lambda value: value["fronts"][0].update(extra=True),
            "contains unsupported fields: extra",
        ),
        (
            lambda value: value["fronts"][0].pop("stakes"),
            "is missing fields: stakes",
        ),
        (
            lambda value: value["story_threads"][0].update(linked_clue_ids="clue"),
            "linked_clue_ids must be a string list",
        ),
        (
            lambda value: value["character_arcs"][0]["opportunities"][0].pop("prompt"),
            "is missing fields: prompt",
        ),
        (
            lambda value: value["scene_links"][0].update(to_scene_id=7),
            "to_scene_id must be a non-empty string",
        ),
        (
            lambda value: value["clues"][0].update(linked_thread_ids=["thread:unknown"]),
            "references unknown thread",
        ),
        (
            lambda value: value["lineage"].pop("parent_module_key"),
            "lineage is missing fields: parent_module_key",
        ),
    ],
)
def test_runtime_nested_schema_and_cross_reference_error_paths(mutation, message) -> None:
    manifest = runtime("emergent_episode", "arkham-seed", 1)["runtime_manifest"]
    mutation(manifest)
    errors = CocModuleProfile().document_metadata(
        "<!-- sagasmith-runtime-manifest\n" + json.dumps(manifest) + "\n-->"
    )["runtime_manifest_errors"]
    assert any(message in error for error in errors)


def test_runtime_all_ten_collections_accept_only_the_exact_cross_referenced_shapes() -> None:
    manifest = runtime("emergent_episode", "arkham-seed", 1)["runtime_manifest"]
    scene_id = "scene:chapter-1"
    manifest["entities"] = [{"id": "entity:captain", "kind": "npc", "name": "Captain Marsh"}]
    manifest["secrets"] = [
        {
            "id": "secret:captain-oath",
            "initial_knowers": ["entity:captain"],
            "reveal_trigger": "The captain is confronted with the ledger.",
        }
    ]
    manifest["plot_nodes"] = [
        {
            "id": "node:ledger-choice",
            "trigger": "The investigators decode the ledger.",
            "consequences": ["The inlet becomes reachable."],
            "linked_thread_ids": ["thread:missing-ship"],
        }
    ]
    manifest["foreshadowing"] = [
        {
            "id": "signal:human-teeth",
            "signal": "Fish wash ashore with human teeth.",
            "reveal_trigger": "The tide cult begins the rite.",
            "linked_thread_ids": ["thread:missing-ship"],
            "payoff_scene_ids": [scene_id],
        }
    ]
    manifest["branches"] = [
        {
            "id": "branch:follow-ledger",
            "trigger": "The investigators choose whether to follow the ledger.",
            "consequences": ["Travel to the inlet", "Remain in Arkham"],
            "scene_ids": [scene_id],
        }
    ]
    assert runtime_manifest_errors(manifest) == []


@pytest.mark.parametrize(
    "collection, value, message",
    [
        ("entities", {"id": "entity:x", "kind": "npc"}, "is missing fields: name"),
        (
            "secrets",
            {"id": "secret:x", "initial_knowers": "entity:x", "reveal_trigger": "Asked"},
            "initial_knowers must be a string list",
        ),
        (
            "plot_nodes",
            {
                "id": "node:x",
                "trigger": "Asked",
                "consequences": [],
                "linked_thread_ids": [],
                "forced_player_outcome": "submit",
            },
            "contains unsupported fields: forced_player_outcome",
        ),
        (
            "foreshadowing",
            {
                "id": "signal:x",
                "signal": "A bell rings.",
                "reveal_trigger": "Midnight",
                "linked_thread_ids": ["thread:unknown"],
                "payoff_scene_ids": [],
            },
            "references unknown thread",
        ),
        (
            "branches",
            {
                "id": "branch:x",
                "trigger": "Choose",
                "consequences": [],
                "scene_ids": [7],
            },
            "scene_ids must be a string list",
        ),
    ],
)
def test_runtime_remaining_collection_schema_error_paths(collection, value, message) -> None:
    manifest = runtime("emergent_episode", "arkham-seed", 1)["runtime_manifest"]
    manifest[collection] = [value]
    errors = runtime_manifest_errors(manifest)
    assert any(message in error for error in errors)
