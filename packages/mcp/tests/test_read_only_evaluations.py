from __future__ import annotations

import asyncio
from pathlib import Path
from xml.etree import ElementTree

from sagasmith_coc_mcp.config import McpConfig
from sagasmith_coc_mcp.server import create_server


async def _call(server, name: str, arguments: dict | None = None):
    result = (await server.call_tool(name, arguments or {})).structured_content
    if isinstance(result, dict):
        return result.get("result", result)
    return result


async def _fixture(server) -> None:
    campaigns: dict[str, dict] = {}
    for name, description in (
        ("Arkham Lantern", "A completed maritime mystery archived in 1926."),
        ("Kingsport Signal", "A completed wireless mystery archived in 1928."),
    ):
        campaigns[name] = await _call(
            server,
            "campaign_change",
            {
                "action": "create",
                "data": {
                    "name": name,
                    "description": description,
                    "idempotency_key": f"evaluation:{name}",
                },
            },
        )
    actors = {
        "Arkham Lantern": [
            ("Alice North", "investigator", "A patient cartographer."),
            ("Borin Shaw", "npc", "A veteran harbor guide."),
            ("Lumen Grey", "npc", "Keeper of an unreliable lantern."),
            ("Nyx Marsh", "npc", "Custodian of the sealed observatory."),
        ],
        "Kingsport Signal": [
            ("Zora Vale", "investigator", "A radio engineer following a coded signal."),
            ("Mira Cole", "npc", "The town archive custodian."),
            ("Ash Wyrm", "creature", "A thing sleeping beneath the transmitter."),
        ],
    }
    for campaign_name, roster in actors.items():
        campaign_id = campaigns[campaign_name]["id"]
        for name, character_type, summary in roster:
            current = await _call(
                server,
                "campaign_query",
                {"action": "get", "campaign_id": campaign_id},
            )
            await _call(
                server,
                "character_change",
                {
                    "action": "create",
                    "campaign_id": campaign_id,
                    "data": {
                        "name": name,
                        "character_type": character_type,
                        "summary": summary,
                        "sheet": {"skills": {"Spot Hidden": 50}},
                        "expected_campaign_revision": current["revision"],
                        "idempotency_key": f"evaluation:{campaign_name}:{name}",
                    },
                },
            )


async def _paged_campaigns(server) -> list[dict]:
    values: list[dict] = []
    cursor = None
    while True:
        page = await _call(
            server,
            "campaign_query",
            {"action": "list", "query": "completed", "limit": 1, "cursor": cursor},
        )
        values.extend(page["campaigns"])
        cursor = page["next_cursor"]
        if cursor is None:
            return values


async def _paged_roster(server, campaign_id: str) -> list[dict]:
    values: list[dict] = []
    cursor = None
    while True:
        page = await _call(
            server,
            "character_query",
            {"action": "list", "campaign_id": campaign_id, "limit": 2, "cursor": cursor},
        )
        values.extend(page["characters"])
        cursor = page["next_cursor"]
        if cursor is None:
            return values


async def _solve(server) -> list[str]:
    campaigns = sorted(await _paged_campaigns(server), key=lambda item: item["name"])
    rosters = {item["id"]: await _paged_roster(server, item["id"]) for item in campaigns}
    details = [
        await _call(
            server,
            "character_query",
            {
                "action": "get",
                "campaign_id": campaign["id"],
                "character_id": actor["id"],
            },
        )
        for campaign in campaigns
        for actor in rosters[campaign["id"]]
    ]
    campaign_by_id = {item["id"]: item for item in campaigns}
    largest = max(campaigns, key=lambda item: len(rosters[item["id"]]))
    last_investigator = max(
        actor["name"] for actor in details if actor["character_type"] == "investigator"
    )
    creature = next(actor for actor in details if actor["character_type"] == "creature")
    npc_count = sum(actor["character_type"] == "npc" for actor in details)
    balanced = next(
        campaign
        for campaign in campaigns
        if sum(actor["character_type"] == "investigator" for actor in rosters[campaign["id"]])
        == sum(actor["character_type"] == "npc" for actor in rosters[campaign["id"]])
    )
    observatory = next(actor for actor in details if "sealed observatory" in actor["summary"])
    kingsport = next(item for item in campaigns if item["name"] == "Kingsport Signal")
    capabilities = await _call(server, "server_capabilities")
    assert capabilities["system"] == campaigns[0]["system_id"]
    return [
        largest["name"],
        last_investigator,
        campaign_by_id[creature["campaign_id"]]["name"],
        str(npc_count),
        str(len(details)),
        balanced["name"],
        observatory["name"],
        str(len({actor["character_type"] for actor in rosters[kingsport["id"]]})),
        capabilities["system"],
        campaigns[0]["slug"],
    ]


def test_builder_evaluations_are_independent_read_only_and_actually_solved(
    tmp_path: Path,
) -> None:
    evaluation_path = Path(__file__).parents[1] / "evaluations" / "read_only.xml"
    root = ElementTree.parse(evaluation_path).getroot()
    pairs = root.findall("qa_pair")
    assert len(pairs) >= 10
    questions = [str(pair.findtext("question") or "").strip() for pair in pairs]
    answers = [str(pair.findtext("answer") or "").strip() for pair in pairs]
    assert len(questions) == len(set(questions))
    assert all(questions) and all(answers)

    async def exercise() -> None:
        server = create_server(
            McpConfig(
                home=tmp_path / "home",
                database_url=None,
                coc_skills_dir=tmp_path / "coc",
                modulegen_skills_dir=tmp_path / "modulegen",
            )
        )
        await _fixture(server)
        catalog = {tool.name: tool for tool in await server.list_tools()}
        for tool_name in ("campaign_query", "character_query", "server_capabilities"):
            annotations = catalog[tool_name].annotations
            assert annotations is not None
            assert annotations.read_only_hint is True
            assert annotations.idempotent_hint is True
        assert await _solve(server) == answers

    asyncio.run(exercise())
