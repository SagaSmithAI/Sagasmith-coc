from __future__ import annotations

from sagasmith_core.modules import MarkdownModuleParser

from sagasmith_coc.module_profile import CocModuleProfile


def test_coc_conventional_scenario_parses_investigation_metadata() -> None:
    parsed = MarkdownModuleParser(profile=CocModuleProfile()).parse(
        "# The Lightless Beacon\n"
        "Keeper introduction.\n"
        "## BACKGROUND\n"
        "What happened before play.\n"
        "## Lighthouse Cottage\n"
        "Search the room.\n"
        "### Core Clue: Torn Letter\n"
        "The investigators find Cassidy's letter.\n"
        "### Hard Spot Hidden Check\n"
        "A successful roll reveals blood.\n"
        "### Sanity Check\n"
        "The corpse causes 0/1D4 SAN loss.\n"
    )

    scenes = parsed[0].scenes
    assert [scene.title for scene in scenes] == [
        "The Lightless Beacon",
        "BACKGROUND",
        "Lighthouse Cottage",
    ]
    assert scenes[0].metadata["scene_type"] == "reference"
    assert scenes[1].metadata["scene_type"] == "reference"
    cottage = scenes[2]
    assert cottage.metadata["scene_type"] == "investigation"
    assert cottage.metadata["visibility"] == "keeper"
    assert cottage.metadata["clues"] == [
        {
            "title": "Core Clue: Torn Letter",
            "line": 7,
            "type": "core_clue",
        }
    ]
    assert cottage.metadata["checks"] == [
        {
            "title": "Hard Spot Hidden Check",
            "line": 9,
            "difficulty": "hard",
        },
        {
            "title": "Sanity Check",
            "line": 11,
            "difficulty": None,
        },
    ]
    assert cottage.metadata["sanity"][0]["success_loss"] == "0"
    assert cottage.metadata["sanity"][0]["failure_loss"] == "1D4"


def test_coc_handout_pack_creates_player_visible_assets() -> None:
    parsed = MarkdownModuleParser(profile=CocModuleProfile()).parse(
        "# Evidence Pack\n"
        "Keeper inventory.\n"
        "## HANDOUT: LIGHTLESS #1\n"
        "A letter from Cassidy.\n"
        "## HANDOUT: LIGHTLESS #2\n"
        "A torn diary page.\n"
    )

    scenes = parsed[0].scenes
    assert [scene.title for scene in scenes] == [
        "Evidence Pack",
        "HANDOUT: LIGHTLESS #1",
        "HANDOUT: LIGHTLESS #2",
    ]
    assert scenes[0].metadata["scene_type"] == "reference"
    assert all(scene.metadata["visibility"] == "player" for scene in scenes[1:])


def test_coc_solo_scenario_creates_nodes_and_choice_edges() -> None:
    nodes = "\n".join(
        f"## **{number}**\n"
        + (f"Go to {number + 1}.\n" if number < 10 else "The End.\n")
        for number in range(1, 11)
    )

    scenes = MarkdownModuleParser(profile=CocModuleProfile()).parse(
        f"# Alone Against the Dark\nInstructions.\n{nodes}"
    )[0].scenes

    assert scenes[0].metadata["scene_type"] == "reference"
    assert [scene.metadata["node_id"] for scene in scenes[1:]] == list(range(1, 11))
    assert scenes[1].metadata["transitions"] == [2]
    assert scenes[-1].metadata["transitions"] == []


def test_coc_page_numbers_without_choices_are_not_solo_nodes() -> None:
    pages = "\n".join(f"##### {number}\nPage text.\n" for number in range(1, 21))

    scenes = MarkdownModuleParser(profile=CocModuleProfile()).parse(
        f"# Conventional Scenario\n{pages}"
    )[0].scenes

    assert all(scene.metadata["scene_type"] != "solo_node" for scene in scenes)
