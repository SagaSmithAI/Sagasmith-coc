from __future__ import annotations

import json
from pathlib import Path

from sagasmith_coc.cli import main


def _call(capsys, *args: str) -> tuple[int, dict]:
    code = main([*args, "--json"])
    output = capsys.readouterr()
    assert output.err == ""
    return code, json.loads(output.out)


def test_coc_skill_cli_vertical_slice(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv(
        "COC7_DATABASE_URL",
        f"sqlite+pysqlite:///{(tmp_path / 'coc.db').as_posix()}",
    )
    code, started = _call(
        capsys,
        "campaign",
        "start",
        "--name",
        "Arkham",
        "--ruleset",
        "classic",
    )
    assert code == 0
    campaign_id = started["data"]["campaign"]["id"]

    code, investigator = _call(
        capsys,
        "investigator",
        "create",
        "--campaign",
        campaign_id,
        "--name",
        "Professor",
        "--sheet",
        '{"characteristics":{"pow":70,"edu":80}}',
    )
    assert code == 0
    assert investigator["data"]["sheet"]["san"] == 70
    investigator_id = investigator["data"]["id"]
    assert _call(
        capsys,
        "investigator",
        "update",
        "--id",
        investigator_id,
        "--sheet",
        '{"characteristics":{"pow":60}}',
    )[0] == 0
    assert _call(capsys, "state", "undo", "--campaign", campaign_id)[0] == 0
    _, restored = _call(capsys, "investigator", "show", "--id", investigator_id)
    assert restored["data"]["sheet"]["san"] == 70

    scenario = tmp_path / "scenario.md"
    scenario.write_text(
        "# 第一章\n## 图书馆\n### 线索\n一封染血的手记藏在书架后。\n",
        encoding="utf-8",
    )
    code, imported = _call(
        capsys,
        "module",
        "ingest",
        "--campaign",
        campaign_id,
        "--path",
        str(scenario),
    )
    assert code == 0
    assert imported["data"]["scenes"] == 2
    _, scene_index = _call(
        capsys,
        "module",
        "index",
        "--campaign",
        campaign_id,
    )
    assert [scene["title"] for scene in scene_index["data"]["scenes"]] == [
        "第一章",
        "图书馆",
    ]
    assert scene_index["data"]["scenes"][1]["scene_type"] == "investigation"
    assert scene_index["data"]["scenes"][1]["visibility"] == "keeper"
    assert scene_index["data"]["scenes"][1]["subsections"] == [
        {"title": "线索", "line": 3, "type": "clue"}
    ]
    assert scene_index["data"]["scenes"][1]["clues"] == [
        {"title": "线索", "line": 3, "type": "clue"}
    ]
    scene_id = scene_index["data"]["scenes"][1]["scene_id"]
    assert _call(
        capsys,
        "module",
        "set-progress",
        "--campaign",
        campaign_id,
        "--scene",
        scene_id,
        "--progress",
        "30",
        "--state",
        '{"discovered_clues":["染血手记"]}',
    )[0] == 0
    current = _call(
        capsys,
        "module",
        "current",
        "--campaign",
        campaign_id,
    )[1]["data"]["scene"]
    assert current["title"] == "图书馆"
    assert current["scope_id"] == "party"
    assert current["clues"][0]["title"] == "线索"
    assert current["progress"]["state"] == {"discovered_clues": ["染血手记"]}
    inherited = _call(
        capsys,
        "module",
        "current",
        "--campaign",
        campaign_id,
        "--scope",
        "player:investigator",
    )[1]["data"]["scene"]
    assert inherited["title"] == "图书馆"
    assert inherited["inherited_from_party"] is True
    assert _call(
        capsys,
        "module",
        "set-progress",
        "--campaign",
        campaign_id,
        "--scope",
        "player:investigator",
        "--scene",
        scene_index["data"]["scenes"][0]["scene_id"],
        "--progress",
        "15",
    )[0] == 0
    personal = _call(
        capsys,
        "module",
        "current",
        "--campaign",
        campaign_id,
        "--scope",
        "player:investigator",
    )[1]["data"]["scene"]
    assert personal["title"] == "第一章"
    assert personal["scope_id"] == "player:investigator"
    party = _call(
        capsys,
        "module",
        "current",
        "--campaign",
        campaign_id,
    )[1]["data"]["scene"]
    assert party["title"] == "图书馆"

    code, result = _call(
        capsys,
        "check",
        "skill",
        "--threshold",
        "70",
        "--roll",
        "30",
    )
    assert code == 0
    assert result["data"]["success"] is True

    _, validated = _call(
        capsys,
        "investigator",
        "validate",
        "--sheet",
        '{"characteristics":{"str":70,"siz":65,"pow":60}}',
    )
    assert validated["data"]["damage_bonus"] == "1D4"
    _, opposed = _call(
        capsys,
        "check",
        "opposed",
        "--payload",
        '{"attacker_roll":20,"attacker_threshold":60,"defender_roll":45,"defender_threshold":50}',
    )
    assert opposed["data"]["winner"] == "attacker"

    code, attack = _call(
        capsys,
        "combat",
        "melee",
        "--threshold",
        "60",
        "--roll",
        "20",
        "--payload",
        '{"weapon_damage":"1D6","damage_bonus":"1D4"}',
    )
    assert code == 0
    assert attack["data"]["hit"] is True
