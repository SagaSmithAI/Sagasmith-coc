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


async def _campaign_rosters(server) -> tuple[list[dict], dict[str, list[dict]]]:
    campaigns = sorted(await _paged_campaigns(server), key=lambda item: item["name"])
    rosters = {item["id"]: await _paged_roster(server, item["id"]) for item in campaigns}
    return campaigns, rosters


async def _detailed_actors(
    server,
    campaigns: list[dict],
    rosters: dict[str, list[dict]],
) -> list[dict]:
    return [
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


async def _solve_largest_roster(server) -> str:
    campaigns, rosters = await _campaign_rosters(server)
    return max(campaigns, key=lambda item: len(rosters[item["id"]]))["name"]


async def _solve_last_investigator(server) -> str:
    campaigns, rosters = await _campaign_rosters(server)
    details = await _detailed_actors(server, campaigns, rosters)
    return max(actor["name"] for actor in details if actor["character_type"] == "investigator")


async def _solve_creature_campaign(server) -> str:
    campaigns, rosters = await _campaign_rosters(server)
    details = await _detailed_actors(server, campaigns, rosters)
    creature = next(actor for actor in details if actor["character_type"] == "creature")
    return next(item["name"] for item in campaigns if item["id"] == creature["campaign_id"])


async def _solve_npc_count(server) -> str:
    campaigns, rosters = await _campaign_rosters(server)
    details = await _detailed_actors(server, campaigns, rosters)
    return str(sum(actor["character_type"] == "npc" for actor in details))


async def _solve_actor_count(server) -> str:
    campaigns, rosters = await _campaign_rosters(server)
    return str(len(await _detailed_actors(server, campaigns, rosters)))


async def _solve_balanced_campaign(server) -> str:
    campaigns, rosters = await _campaign_rosters(server)
    return next(
        campaign["name"]
        for campaign in campaigns
        if sum(actor["character_type"] == "investigator" for actor in rosters[campaign["id"]])
        == sum(actor["character_type"] == "npc" for actor in rosters[campaign["id"]])
    )


async def _solve_observatory_custodian(server) -> str:
    campaigns, rosters = await _campaign_rosters(server)
    details = await _detailed_actors(server, campaigns, rosters)
    return next(actor["name"] for actor in details if "sealed observatory" in actor["summary"])


async def _solve_kingsport_classifications(server) -> str:
    campaigns, rosters = await _campaign_rosters(server)
    kingsport = next(item for item in campaigns if item["name"] == "Kingsport Signal")
    details = await _detailed_actors(server, [kingsport], rosters)
    return str(len({actor["character_type"] for actor in details}))


async def _solve_shared_system(server) -> str:
    campaigns = await _paged_campaigns(server)
    details = [
        await _call(
            server,
            "campaign_query",
            {"action": "get", "campaign_id": campaign["id"]},
        )
        for campaign in campaigns
    ]
    capabilities = await _call(server, "server_capabilities")
    assert {item["system_id"] for item in details} == {capabilities["system"]}
    return capabilities["system"]


async def _solve_first_slug(server) -> str:
    campaigns = sorted(await _paged_campaigns(server), key=lambda item: item["name"])
    selected = await _call(
        server,
        "campaign_query",
        {"action": "get", "campaign_id": campaigns[0]["id"]},
    )
    assert await _paged_roster(server, selected["id"])
    return selected["slug"]


async def _solve_independently(server) -> list[str]:
    solvers = (
        _solve_largest_roster,
        _solve_last_investigator,
        _solve_creature_campaign,
        _solve_npc_count,
        _solve_actor_count,
        _solve_balanced_campaign,
        _solve_observatory_custodian,
        _solve_kingsport_classifications,
        _solve_shared_system,
        _solve_first_slug,
    )
    return [await solver(server) for solver in solvers]


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
        assert await _solve_independently(server) == answers

    asyncio.run(exercise())
