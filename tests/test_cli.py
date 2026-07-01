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
    assert imported["data"]["scenes"] == 1

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
