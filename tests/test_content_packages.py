from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from sagasmith_core.campaigns import CampaignService
from sagasmith_core.content_pack import dumps_content_archive, loads_content_archive
from sagasmith_core.database import Database, sqlite_database_url
from sagasmith_core.modules import MarkdownModuleParser, ModuleService

from sagasmith_coc.content_packages import (
    build_module_content_package,
)
from sagasmith_coc.module_profile import CocModuleProfile


@pytest.fixture
def database(tmp_path: Path):
    value = Database(sqlite_database_url(tmp_path / "test.db"))
    value.create_schema()
    yield value
    value.dispose()


def test_solo_module_ingest_uses_core_visibility_contract(database: Database) -> None:
    nodes = "\n".join(
        f"## {number}\n"
        + (f"Go to {number + 1}.\n" if number < 10 else "The End.\n")
        for number in range(1, 11)
    )
    campaign = CampaignService(database).create(system_id="coc7e", name="Solo authoring")
    modules = ModuleService(database)

    imported = modules.ingest(
        campaign_id=campaign.id,
        source_key="solo.md",
        title="Solo",
        content=f"# Solo\nInstructions.\n{nodes}",
        parser=MarkdownModuleParser(profile=CocModuleProfile()),
        activate=False,
    )

    scenes = modules.scene_index(campaign.id, module_id=imported.module_id)
    assert len(scenes) == 11
    assert all(scene["visibility"] == "party" for scene in scenes[1:])


def test_reviewed_scenario_compiles_to_round_trip_v2_pack(database: Database) -> None:
    source_text = (
        "# The Lantern Case\n"
        "## Arrival\n"
        "Two to four investigators arrive in Arkham in the 1920s.\n"
        "## Cellar\n"
        "### Core Clue\nThe ledger reveals the hidden door.\n"
        "## Ending\nThe investigators seal the door.\n"
    )
    campaign = CampaignService(database).create(system_id="coc7e", name="Authoring")
    modules = ModuleService(database)
    imported = modules.ingest(
        campaign_id=campaign.id,
        source_key="lantern-case.md",
        title="The Lantern Case",
        content=source_text,
        parser=MarkdownModuleParser(profile=CocModuleProfile()),
        activate=True,
    )
    scene = modules.scene_index(campaign.id, module_id=imported.module_id)[0]
    evidence = modules.search(
        campaign_id=campaign.id,
        query="Two to four",
        module_ids=[imported.module_id],
    )[0]
    receipt = {
        "source_key": "lantern-case.md",
        "page": None,
        "chunk_hash": hashlib.sha256(evidence.content.encode("utf-8")).hexdigest(),
        "note": "Reviewed scenario profile evidence.",
    }
    descriptor = modules.export_content_descriptor(
        campaign.id,
        imported.module_id,
        package_id="coc7e.module.lantern-case",
        version="1.0.0",
        manifest={
            "title": "The Lantern Case",
            "classification": "scenario",
            "compatibility": {"editions": ["7e"], "required_capabilities": ["module_pack_v2"]},
            "play_profile": {
                "investigator_count": {"minimum": 2, "maximum": 4, "source_refs": [receipt]},
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
        catalogs={
            "clues": [{"id": "clue:ledger", "source_refs": [receipt]}],
            "handouts": [],
            "encounters": [],
            "hazards": [],
            "tomes": [],
            "spells": [],
            "mechanics": [],
        },
        narrative={
            "dossiers": [],
            "endings": [{"id": "ending:sealed", "trigger": "seal the door", "consequences": []}],
        },
        metadata={
            "license": "private",
            "attribution": "Synthetic test source",
            "agent_finalization": {
                "confirmed": True,
                "reviewer": "agent:test",
                "note": "Reviewed source, profile, clues, scenes, ending, and dependencies.",
            },
        },
    )

    package, blobs = build_module_content_package(descriptor, {})
    assert package["format"] == "sagasmith.content-package"
    assert package["schema_version"] == 2
    assert package["system_id"] == "coc7e"
    assert package["kind"] == "module"
    assert package["content"]["scene_atlas"][0]["stable_key"] == scene["stable_key"]
    loaded, loaded_blobs = loads_content_archive(dumps_content_archive(package, blobs))
    assert loaded == package
    assert loaded_blobs == blobs


def test_final_module_rejects_unsourced_profile_decisions(database: Database) -> None:
    source = "# Case\n## Scene\nOne investigator.\n"
    campaign = CampaignService(database).create(system_id="coc7e", name="Authoring")
    modules = ModuleService(database)
    imported = modules.ingest(
        campaign_id=campaign.id,
        source_key="case.md",
        title="Case",
        content=source,
        parser=MarkdownModuleParser(profile=CocModuleProfile()),
        activate=False,
    )
    descriptor = modules.export_content_descriptor(
        campaign.id,
        imported.module_id,
        package_id="coc7e.module.case",
        manifest={
            "title": "Case",
            "classification": "scenario",
            "compatibility": {"editions": ["7e"]},
            "play_profile": {
                "investigator_count": {"minimum": 1, "maximum": 1, "source_refs": []},
                "ruleset": {"supported": ["classic"], "recommended": "classic", "source_refs": []},
                "era": {"value": "1920s", "source_refs": []},
                "estimated_sessions": {"minimum": 1, "maximum": 1, "source_refs": []},
                "pregenerated_characters": {"available": False, "source_refs": []},
                "solo_play": {"supported": False, "source_refs": []},
            },
            "continuity": {},
            "activation": {"mode": "campaign_attach", "default_active": False},
        },
        catalogs={
            key: []
            for key in (
                "clues",
                "handouts",
                "encounters",
                "hazards",
                "tomes",
                "spells",
                "mechanics",
            )
        },
        narrative={"dossiers": [], "endings": [{"id": "ending:end"}]},
        metadata={
            "agent_finalization": {"confirmed": True, "reviewer": "agent:test", "note": "Reviewed."}
        },
    )
    with pytest.raises(ValueError, match="requires at least one source_ref"):
        build_module_content_package(descriptor, {})
