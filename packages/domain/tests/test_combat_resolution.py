from sagasmith_coc.engine.combat_resolution import (
    combat_attack_profile,
    resolve_combat_attack,
)
from sagasmith_coc.engine.combat_state import start_combat
from sagasmith_coc.random_stream import CampaignRandomStream, use_random_stream
from sagasmith_coc.system import validate_investigator_sheet


def sheet(*, firearm: bool = False) -> dict:
    weapon = {
        "name": "Revolver" if firearm else "Knife",
        "skill": {"name": "Handgun" if firearm else "Fighting"},
        "damage": "1D6" if firearm else "1D4+DB",
        "ammo": 6 if firearm else None,
        "properties": {"rngd": firearm},
    }
    return validate_investigator_sheet(
        {
            "characteristics": {"dex": 60, "con": 60},
            "skills": {"Fighting": 55, "Handgun": 60},
            "weapons": [weapon],
            "hp": 12,
            "max_hp": 12,
            "dodge": 30,
        }
    )


def combat() -> dict:
    return start_combat(
        [
            {"actor_id": "attacker", "name": "A", "side": "a", "dex": 70},
            {"actor_id": "target", "name": "T", "side": "b", "dex": 50},
        ],
        positioning_mode="agent",
        source="Keeper ruling",
    )


def test_attack_profile_owns_weapon_threshold_and_response_options() -> None:
    melee = combat_attack_profile(sheet(), "knife")
    assert melee["attacker_threshold"] == 55
    assert melee["response_options"] == ["none", "dodge", "fight-back"]
    ranged = combat_attack_profile(sheet(firearm=True), "Revolver")
    assert ranged["response_options"] == ["none", "dive_for_cover"]


def test_ranged_transition_uses_caller_stream_and_consumes_ammunition() -> None:
    attacker = sheet(firearm=True)
    profile = combat_attack_profile(attacker, "Revolver")
    pending = {
        "attacker_id": "attacker",
        "target_actor_id": "target",
        "range_band": "normal",
        **profile,
    }
    stream = CampaignRandomStream.from_campaign_state(
        "campaign",
        {},
        operation="combat",
        idempotency_key="attack-1",
    )
    with use_random_stream(stream):
        result = resolve_combat_attack(
            combat(),
            attacker,
            sheet(),
            pending,
            defense="none",
            attacker_name="A",
            target_name="T",
        )
    assert result["combat"]["pending_choice"] is None
    assert result["sheet_updates"]["attacker"]["weapons"][0]["ammo"] == 5
    assert stream.draw_count >= 2
