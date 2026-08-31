"""CoC 7e compilation and validation for unified content-package v2 archives."""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping
from typing import Any

from sagasmith_core.content_pack import (
    blob_descriptor,
    build_content_package,
    build_source_bundle,
    source_ref,
)
from sagasmith_core.content_pack import (
    validate_content_package as validate_core_content_package,
)

from sagasmith_coc.module_profile import runtime_manifest_errors
from sagasmith_coc.system import validate_investigator_sheet

COC_SYSTEM_ID = "coc7e"
MODULE_CLASSIFICATIONS = frozenset({"scenario", "campaign", "solo_adventure", "handout_pack"})
COC_RULESETS = frozenset({"classic", "pulp"})
MODULE_PLAY_PROFILE_FIELDS = frozenset(
    {
        "investigator_count",
        "ruleset",
        "era",
        "estimated_sessions",
        "pregenerated_characters",
        "solo_play",
    }
)
MODULE_CATALOG_FIELDS = frozenset(
    {"clues", "handouts", "encounters", "hazards", "tomes", "spells", "mechanics"}
)
RUNTIME_DESIGN_CLASSIFICATIONS = frozenset(
    {"authored_scenario", "emergent_seed", "emergent_episode"}
)


def build_rule_content_package(
    *,
    package_id: str,
    version: str,
    title: str,
    exported_sources: list[tuple[Mapping[str, Any], Mapping[str, Any], bytes]],
    metadata: Mapping[str, Any] | None = None,
    dependencies: list[Mapping[str, Any]] | None = None,
    artifacts: list[Mapping[str, Any]] | None = None,
    mechanics: list[Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Compile reviewed Core rule sources into a CoC schema-v2 rules Pack.

    Rule interpretation stays in reviewed artifacts/mechanics.  This compiler
    only binds immutable source evidence and the current unified Pack schema.
    """

    if not exported_sources:
        raise ValueError("a CoC rules Pack requires at least one reviewed source")
    sources: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    blobs: dict[str, bytes] = {}
    for raw_source, raw_asset, raw_blob in exported_sources:
        source = copy.deepcopy(dict(raw_source))
        asset = copy.deepcopy(dict(raw_asset))
        blob = bytes(raw_blob)
        checksum = str(asset.get("checksum") or "")
        if not checksum or checksum in blobs:
            raise ValueError("CoC rules Pack source assets require unique checksums")
        sources.append(source)
        assets.append(asset)
        blobs[checksum] = blob
    package_metadata = {
        "license": "private",
        "attribution": "User supplied source",
        **copy.deepcopy(dict(metadata or {})),
    }
    manifest = {
        "id": package_id,
        "version": version,
        "system_id": COC_SYSTEM_ID,
        "title": title,
        "classification": "core_rules",
        "editions": ["7e"],
        "activation": {"rule_policy": "branch"},
    }
    content = {
        "classification": "core_rules",
        "editions": ["7e"],
        "activation": {"rule_policy": "branch"},
        "conflicts": [],
        "rule_definitions": [],
        "artifacts": copy.deepcopy(list(artifacts or [])),
        "mechanics": copy.deepcopy(list(mechanics or [])),
    }
    package = build_content_package(
        kind="core_rules",
        package_id=package_id,
        version=version,
        system_id=COC_SYSTEM_ID,
        manifest=manifest,
        dependencies=copy.deepcopy(list(dependencies or [])),
        sources=sources,
        assets=assets,
        content_reviews=[],
        actors=[],
        content=content,
        metadata=package_metadata,
    )
    return validate_coc_content_package(package), blobs


def _require_source_refs(value: Mapping[str, Any], field: str) -> None:
    refs = value.get("source_refs")
    if not isinstance(refs, list) or not refs or any(not isinstance(ref, Mapping) for ref in refs):
        raise ValueError(f"{field} requires at least one source_ref")


def _validate_module_profile(value: Mapping[str, Any]) -> None:
    unknown = sorted(set(value) - MODULE_PLAY_PROFILE_FIELDS)
    missing = sorted(MODULE_PLAY_PROFILE_FIELDS - set(value))
    if unknown or missing:
        details = []
        if unknown:
            details.append("unsupported fields: " + ", ".join(unknown))
        if missing:
            details.append("missing fields: " + ", ".join(missing))
        raise ValueError("CoC module play_profile has " + "; ".join(details))

    investigator_count = value["investigator_count"]
    if not isinstance(investigator_count, Mapping):
        raise ValueError("CoC module play_profile.investigator_count must be an object")
    minimum = investigator_count.get("minimum")
    maximum = investigator_count.get("maximum")
    if (
        any(
            isinstance(item, bool) or not isinstance(item, int) or item < 1
            for item in (minimum, maximum)
        )
        or maximum < minimum
    ):
        raise ValueError(
            "CoC module play_profile.investigator_count requires minimum/maximum "
            "as a valid positive range"
        )
    _require_source_refs(investigator_count, "CoC module play_profile.investigator_count")

    ruleset = value["ruleset"]
    if not isinstance(ruleset, Mapping):
        raise ValueError("CoC module play_profile.ruleset must be an object")
    supported = ruleset.get("supported")
    recommended = str(ruleset.get("recommended") or "")
    if (
        not isinstance(supported, list)
        or not supported
        or any(str(item) not in COC_RULESETS for item in supported)
        or recommended not in supported
    ):
        raise ValueError(
            "CoC module ruleset requires supported classic/pulp values and a recommendation"
        )
    _require_source_refs(ruleset, "CoC module ruleset")

    for field in ("era", "estimated_sessions", "pregenerated_characters", "solo_play"):
        item = value[field]
        if not isinstance(item, Mapping):
            raise ValueError(f"CoC module play_profile.{field} must be an object")
        _require_source_refs(item, f"CoC module {field}")
    if not str(value["era"].get("value") or "").strip():
        raise ValueError("CoC module era.value is required")
    session_min = value["estimated_sessions"].get("minimum")
    session_max = value["estimated_sessions"].get("maximum")
    if (
        any(
            isinstance(item, bool) or not isinstance(item, int) or item < 1
            for item in (session_min, session_max)
        )
        or session_max < session_min
    ):
        raise ValueError(
            "CoC module play_profile.estimated_sessions requires minimum/maximum "
            "as a valid positive range"
        )
    for field, key in (("pregenerated_characters", "available"), ("solo_play", "supported")):
        if not isinstance(value[field].get(key), bool):
            raise ValueError(f"CoC module {field}.{key} must be a boolean")


def validate_module_pack_decisions(value: Mapping[str, Any]) -> None:
    """Validate each supplied Module Pack draft decision before it is persisted."""

    manifest = value.get("manifest")
    if manifest is not None:
        if not isinstance(manifest, Mapping):
            raise ValueError("module Pack manifest must be an object")
        required = {
            "title",
            "classification",
            "compatibility",
            "play_profile",
            "continuity",
            "activation",
        }
        missing = sorted(required - set(manifest))
        unsupported = sorted(set(manifest) - required)
        if missing or unsupported:
            details = []
            if missing:
                details.append("missing fields: " + ", ".join(missing))
            if unsupported:
                details.append("unsupported fields: " + ", ".join(unsupported))
            raise ValueError("module Pack manifest has " + "; ".join(details))
        title = str(manifest.get("title") or "").strip()
        if not 1 <= len(title) <= 500:
            raise ValueError("module Pack manifest.title must contain 1 to 500 characters")
        classification = str(manifest.get("classification") or "")
        if classification not in MODULE_CLASSIFICATIONS:
            raise ValueError(
                "module Pack manifest.classification must be scenario, campaign, "
                "solo_adventure, or handout_pack"
            )
        compatibility = manifest.get("compatibility")
        if not isinstance(compatibility, Mapping):
            raise ValueError("module Pack manifest.compatibility must be an object")
        editions = compatibility.get("editions")
        if not isinstance(editions, list) or "7e" not in editions:
            raise ValueError("module Pack manifest.compatibility.editions must include 7e")
        profile = manifest.get("play_profile")
        if not isinstance(profile, Mapping):
            raise ValueError("module Pack manifest.play_profile must be an object")
        _validate_module_profile(profile)
        continuity = manifest.get("continuity")
        if not isinstance(continuity, Mapping):
            raise ValueError("module Pack manifest.continuity must be an object")
        continuity_fields = {"series_id", "order", "continues_from", "state_policy"}
        if set(continuity) != continuity_fields:
            raise ValueError(
                "module Pack manifest.continuity requires exactly series_id, order, "
                "continues_from, and state_policy"
            )
        if not isinstance(continuity.get("state_policy"), Mapping):
            raise ValueError("module Pack manifest.continuity.state_policy must be an object")
        activation = manifest.get("activation")
        if not isinstance(activation, Mapping):
            raise ValueError("module Pack manifest.activation must be an object")
        if set(activation) != {"mode", "default_active"}:
            raise ValueError(
                "module Pack manifest.activation requires exactly mode and default_active"
            )
        if activation.get("mode") != "campaign_attach":
            raise ValueError("module Pack manifest.activation.mode must be campaign_attach")
        if not isinstance(activation.get("default_active"), bool):
            raise ValueError("module Pack manifest.activation.default_active must be a boolean")

    catalogs = value.get("catalogs")
    if catalogs is not None:
        if not isinstance(catalogs, Mapping):
            raise ValueError("module Pack catalogs must be an object")
        missing = sorted(MODULE_CATALOG_FIELDS - set(catalogs))
        unsupported = sorted(set(catalogs) - MODULE_CATALOG_FIELDS)
        non_arrays = sorted(name for name, items in catalogs.items() if not isinstance(items, list))
        if missing or unsupported or non_arrays:
            raise ValueError(
                "module Pack catalogs must contain exactly clues, handouts, encounters, "
                "hazards, tomes, spells, and mechanics arrays"
            )

    narrative = value.get("narrative")
    if narrative is not None:
        if not isinstance(narrative, Mapping):
            raise ValueError("module Pack narrative must be an object")
        if set(narrative) != {"dossiers", "endings"} or any(
            not isinstance(narrative.get(field), list) for field in ("dossiers", "endings")
        ):
            raise ValueError("module Pack narrative requires exactly dossiers and endings arrays")

    dependencies = value.get("dependencies")
    if dependencies is not None and (
        not isinstance(dependencies, list)
        or any(not isinstance(item, Mapping) for item in dependencies)
    ):
        raise ValueError("module Pack dependencies must be an array of objects")
    metadata = value.get("metadata")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise ValueError("module Pack metadata must be an object")
    runtime_design = value.get("runtime_design")
    if runtime_design is not None:
        if not isinstance(runtime_design, Mapping):
            raise ValueError("module Pack runtime_design must be an object")
        if errors := runtime_manifest_errors(dict(runtime_design)):
            raise ValueError("invalid module Pack runtime_design: " + "; ".join(errors))
    version = value.get("version")
    if version is not None and not str(version).strip():
        raise ValueError("module Pack version must not be empty")


def validate_coc_content_package(package: Mapping[str, Any]) -> dict[str, Any]:
    """Validate CoC-specific meaning layered on Core's unified Pack contract."""

    value = validate_core_content_package(package)
    if value["system_id"] != COC_SYSTEM_ID:
        return value
    for index, actor in enumerate(value["actors"]):
        actor_type = str(actor.get("actor_type") or "")
        if actor_type not in {"investigator", "npc", "creature"}:
            raise ValueError(f"CoC actor {index} has an unsupported actor_type")
        try:
            validate_investigator_sheet(dict(actor["sheet"]))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"CoC actor {index} has an invalid sheet: {exc}") from exc

    if value["kind"] != "module":
        return value
    finalization = value["metadata"].get("agent_finalization")
    if not isinstance(finalization, Mapping) or set(finalization) != {
        "confirmed",
        "reviewer",
        "note",
    }:
        raise ValueError(
            "CoC module metadata.agent_finalization must contain exactly "
            "confirmed, reviewer, and note"
        )
    if finalization["confirmed"] is not True:
        raise ValueError("CoC module requires explicit Agent confirmation")
    for field in ("reviewer", "note"):
        text = str(finalization[field] or "").strip()
        if not text or len(text) > 2000:
            raise ValueError(f"CoC module agent_finalization.{field} requires 1 to 2000 characters")

    content = value["content"]
    classification = str(content.get("classification") or "")
    if classification not in MODULE_CLASSIFICATIONS:
        raise ValueError("CoC module classification is unsupported")
    compatibility = content.get("compatibility")
    if not isinstance(compatibility, Mapping):
        raise ValueError("CoC module compatibility must be an object")
    editions = compatibility.get("editions")
    if not isinstance(editions, list) or "7e" not in editions:
        raise ValueError("CoC module compatibility.editions must include 7e")
    _validate_module_profile(dict(content.get("play_profile") or {}))

    catalogs = content.get("catalogs")
    if not isinstance(catalogs, Mapping):
        raise ValueError("CoC module catalogs must be an object")
    missing_catalogs = sorted(MODULE_CATALOG_FIELDS - set(catalogs))
    unknown_catalogs = sorted(set(catalogs) - MODULE_CATALOG_FIELDS)
    invalid_catalogs = sorted(key for key, items in catalogs.items() if not isinstance(items, list))
    if missing_catalogs or unknown_catalogs or invalid_catalogs:
        raise ValueError(
            "CoC module catalogs do not match the current contract: "
            f"missing={missing_catalogs}, unsupported={unknown_catalogs}, "
            f"non_arrays={invalid_catalogs}"
        )
    narrative = content.get("narrative")
    if (
        not isinstance(narrative, Mapping)
        or not isinstance(narrative.get("dossiers"), list)
        or not isinstance(narrative.get("endings"), list)
    ):
        raise ValueError("CoC module narrative requires dossiers and endings arrays")
    runtime_design = content.get("runtime_design")
    runtime_classification = "authored_scenario"
    if runtime_design is not None:
        if not isinstance(runtime_design, Mapping):
            raise ValueError("CoC module runtime_design must be an object")
        if errors := runtime_manifest_errors(dict(runtime_design)):
            raise ValueError("invalid CoC runtime_design: " + "; ".join(errors))
        runtime_classification = str(runtime_design.get("classification") or "")
        if runtime_classification not in RUNTIME_DESIGN_CLASSIFICATIONS:
            raise ValueError("CoC module runtime_design classification is unsupported")
        lineage = runtime_design.get("lineage")
        if not isinstance(lineage, Mapping):
            raise ValueError("CoC module runtime_design requires lineage")
        root_module_key = str(lineage.get("root_module_key") or "")
        parent_module_key = str(lineage.get("parent_module_key") or "")
        generation = lineage.get("generation")
        if not root_module_key:
            raise ValueError("CoC module runtime_design requires root_module_key")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise ValueError("CoC module runtime_design generation must be non-negative")
        if runtime_classification in {"authored_scenario", "emergent_seed"} and (
            parent_module_key or generation != 0
        ):
            raise ValueError("runtime design roots must be generation 0 with no parent")
        if runtime_classification in {"emergent_seed", "emergent_episode"} and not list(
            content.get("scene_atlas") or []
        ):
            raise ValueError("emergent CoC module shards require a Scene Atlas scene")
        if runtime_classification == "emergent_episode" and (
            not parent_module_key or generation < 1
        ):
            raise ValueError(
                "emergent_episode runtime_design requires a parent and positive generation"
            )
    if (
        classification in {"campaign", "scenario", "solo_adventure"}
        and runtime_classification not in {"emergent_seed", "emergent_episode"}
        and not narrative["endings"]
    ):
        raise ValueError("playable CoC modules require at least one reachable ending")
    if classification == "solo_adventure" and not content["play_profile"]["solo_play"]["supported"]:
        raise ValueError("solo_adventure requires play_profile.solo_play.supported")
    return value


def _module_source_bundle(
    descriptor: Mapping[str, Any],
    *,
    license: str,
    attribution: str,
) -> tuple[dict[str, Any], dict[str, Any], bytes, dict[str, str]]:
    source_value = dict(descriptor["source"])
    document = str(descriptor["document"]["content"])
    source_key = str(source_value["source_key"])
    sections: list[dict[str, Any]] = []
    chunk_hash_keys: dict[str, str] = {}
    cursor = 0
    for ordinal, scene in enumerate(descriptor["scene_atlas"]):
        scene_content = str(scene["content"])
        scene_metadata = dict(scene.get("metadata") or {})
        scene_start = scene_metadata.get("absolute_start")
        scene_end = scene_metadata.get("absolute_end")
        if not (
            isinstance(scene_start, int)
            and isinstance(scene_end, int)
            and 0 <= scene_start <= scene_end <= len(document)
        ):
            scene_start = document.find(scene_content, cursor)
            if scene_start < 0:
                scene_start = document.find(scene_content)
            scene_end = scene_start + len(scene_content) if scene_start >= 0 else -1
        if scene_start < 0:
            raise ValueError(f"module scene {scene['stable_key']} is not in its document")
        cursor = scene_end
        chunks = []
        chunk_cursor = scene_start
        for chunk_index, raw_chunk in enumerate(scene["chunks"]):
            chunk_content = str(raw_chunk["content"])
            metadata = copy.deepcopy(dict(raw_chunk.get("metadata") or {}))
            chunk_start = metadata.get("absolute_start")
            chunk_end = metadata.get("absolute_end")
            if not (
                isinstance(chunk_start, int)
                and isinstance(chunk_end, int)
                and scene_start <= chunk_start <= chunk_end <= scene_end
            ):
                chunk_start = document.find(chunk_content, chunk_cursor, scene_end)
                if chunk_start < 0:
                    chunk_start = document.find(chunk_content, scene_start, scene_end)
                chunk_end = chunk_start + len(chunk_content) if chunk_start >= 0 else -1
            if chunk_start < 0:
                raise ValueError(f"module scene {scene['stable_key']} chunk is not in its document")
            chunk_cursor = chunk_end
            old_hash = str(raw_chunk.get("content_hash") or "")
            content_hash = hashlib.sha256(
                document[chunk_start:chunk_end].encode("utf-8")
            ).hexdigest()
            chunk_key = (
                f"{source_key}/scene/{scene['stable_key']}/chunk/{chunk_index}-{content_hash[:24]}"
            )
            chunk_hash_keys.setdefault(old_hash or content_hash, chunk_key)
            chunks.append(
                {
                    "key": chunk_key,
                    "ordinal": int(raw_chunk.get("ordinal", chunk_index)),
                    "heading_path": list(raw_chunk.get("heading_path") or [scene["title"]]),
                    "start_offset": chunk_start,
                    "end_offset": chunk_end,
                    "token_count": len(document[chunk_start:chunk_end].split()),
                    "page_start": metadata.get("page_start", scene.get("page_start")),
                    "page_end": metadata.get("page_end", scene.get("page_end")),
                    "metadata": metadata,
                }
            )
        sections.append(
            {
                "ordinal": ordinal,
                "parent_ordinal": None,
                "level": 2,
                "title": str(scene["title"]),
                "path": [str(scene["chapter"]), str(scene["title"])],
                "start_offset": scene_start,
                "end_offset": scene_end,
                "chunks": chunks,
            }
        )
    source, asset, blob = build_source_bundle(
        source_key=source_key,
        title=str(source_value["title"]),
        normalized_text=document,
        edition="7e",
        locale=str(dict(source_value.get("metadata") or {}).get("locale") or ""),
        authority="module",
        sections=sections,
        metadata={
            **copy.deepcopy(dict(source_value.get("metadata") or {})),
            "parser_profile": source_value.get("parser_profile"),
            "parser_version": source_value.get("parser_version"),
        },
        license=license,
        attribution=attribution,
    )
    return source, asset, blob, chunk_hash_keys


def _module_scene_metadata(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Separate Core scene fields from CoC profile data in the portable Pack."""

    metadata = copy.deepcopy(dict(raw))
    canonical_fields = {
        "visibility",
        "scene_level",
        "line_count",
        "subsections",
        "tags",
        "spatial",
    }
    ignored_fields = {
        "absolute_end",
        "absolute_start",
        "content_checksum",
        "end_line",
        "headings",
        "keywords",
        "page_end",
        "page_start",
        "stable_key",
        "start_line",
    }
    existing_profile_data = metadata.pop("profile_data", {})
    if not isinstance(existing_profile_data, Mapping):
        raise ValueError("module scene metadata.profile_data must be an object")
    profile_data = copy.deepcopy(dict(existing_profile_data))
    profile_data.update(
        {
            key: value
            for key, value in metadata.items()
            if key not in canonical_fields | ignored_fields
        }
    )
    return {
        "visibility": metadata.get("visibility", "restricted"),
        "scene_level": metadata.get("scene_level"),
        "line_count": metadata.get("line_count"),
        "subsections": list(metadata.get("subsections") or []),
        "tags": list(metadata.get("tags") or []),
        "spatial": copy.deepcopy(dict(metadata.get("spatial") or {})),
        "profile_data": profile_data,
    }


def _translate_module_refs(
    value: Any,
    *,
    source_key: str,
    chunk_hash_keys: Mapping[str, str],
) -> Any:
    if isinstance(value, list):
        return [
            _translate_module_refs(item, source_key=source_key, chunk_hash_keys=chunk_hash_keys)
            for item in value
        ]
    if not isinstance(value, dict):
        return copy.deepcopy(value)
    if set(value) == {"source_key", "page", "chunk_hash", "note"}:
        chunk_hash = str(value.get("chunk_hash") or "")
        chunk_key = chunk_hash_keys.get(chunk_hash)
        if chunk_key is None:
            raise ValueError(
                "module source_ref.chunk_hash does not match draft evidence; "
                "copy source_ref verbatim from module_draft(evidence)"
            )
        return source_ref(
            source_key=source_key,
            chunk_key=chunk_key,
            page=value.get("page"),
            note=str(value.get("note") or ""),
        )
    return {
        key: _translate_module_refs(item, source_key=source_key, chunk_hash_keys=chunk_hash_keys)
        for key, item in value.items()
    }


def build_module_content_package(
    descriptor: Mapping[str, Any],
    archive_blobs: Mapping[str, bytes],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Compile one reviewed Core module descriptor into a CoC v2 Module Pack."""

    if str(descriptor.get("system_id") or "") != COC_SYSTEM_ID:
        raise ValueError("CoC module compiler requires system_id='coc7e'")
    package_metadata = {
        **copy.deepcopy(dict(descriptor.get("metadata") or {})),
        **copy.deepcopy(dict(metadata or {})),
    }
    license = str(package_metadata.get("license") or "private")
    attribution = str(package_metadata.get("attribution") or "User supplied source")
    source, document_asset, document_blob, hash_keys = _module_source_bundle(
        descriptor,
        license=license,
        attribution=attribution,
    )
    assets = [document_asset]
    blobs = {document_asset["checksum"]: document_blob}
    original_asset_keys = []
    for raw_asset in descriptor.get("assets") or []:
        checksum = str(raw_asset["checksum"])
        raw = archive_blobs[checksum]
        asset = blob_descriptor(
            asset_key=str(raw_asset["asset_key"]),
            kind=str(dict(raw_asset.get("metadata") or {}).get("asset_kind") or "source_asset"),
            name=str(raw_asset["name"]),
            media_type=str(raw_asset["media_type"]),
            content=raw,
            license=license,
            attribution=attribution,
            metadata=dict(raw_asset.get("metadata") or {}),
        )
        assets.append(asset)
        blobs[asset["checksum"]] = raw
        if asset["media_type"] == "application/pdf":
            original_asset_keys.append(asset["asset_key"])
    source["original_asset_keys"] = original_asset_keys
    translated_manifest = _translate_module_refs(
        descriptor["manifest"], source_key=source["source_key"], chunk_hash_keys=hash_keys
    )
    scenes = []
    for raw_scene, source_section in zip(
        descriptor["scene_atlas"], source["sections"], strict=True
    ):
        scene = {
            key: copy.deepcopy(item)
            for key, item in raw_scene.items()
            if key not in {"content", "content_checksum", "chunks"}
        }
        scene["metadata"] = _module_scene_metadata(scene.get("metadata") or {})
        scene["source_span"] = {
            "source_key": source["source_key"],
            "start_offset": source_section["start_offset"],
            "end_offset": source_section["end_offset"],
        }
        scene["source_refs"] = [
            source_ref(
                source_key=source["source_key"],
                chunk_key=chunk["key"],
                page=chunk.get("page_start"),
                note=f"Scene source for {raw_scene['title']}",
            )
            for chunk in source_section["chunks"]
        ]
        scenes.append(scene)
    reviews = []
    for index, raw_review in enumerate(descriptor.get("content_reviews") or []):
        evidence = dict(raw_review.get("evidence") or {})
        refs = [
            source_ref(
                source_key=source["source_key"],
                chunk_key=hash_keys[chunk_hash],
                page=None,
                note="Reviewed scenario content evidence",
            )
            for chunk_hash in evidence.get("chunk_hashes") or []
            if chunk_hash in hash_keys
        ]
        reviews.append(
            {
                "id": f"review.{index}",
                "kind": str(raw_review["content_kind"]),
                "status": "accepted",
                "target": {
                    "scene_key": raw_review["scene_key"],
                    "content_key": raw_review["content_key"],
                },
                "normalized_content": raw_review["normalized_content"],
                "evidence": {
                    "asset_key": evidence.get("asset_key"),
                    "page": evidence.get("page"),
                },
                "source_refs": refs,
                "review": {
                    "reviewer": evidence.get("reviewer"),
                    "observation": evidence.get("observation"),
                },
                "metadata": copy.deepcopy(dict(raw_review.get("metadata") or {})),
            }
        )
    content = {
        "classification": translated_manifest["classification"],
        "compatibility": translated_manifest["compatibility"],
        "play_profile": translated_manifest["play_profile"],
        "continuity": translated_manifest["continuity"],
        "activation": translated_manifest["activation"],
        "scene_atlas": scenes,
        "catalogs": _translate_module_refs(
            descriptor["catalogs"], source_key=source["source_key"], chunk_hash_keys=hash_keys
        ),
        "narrative": _translate_module_refs(
            descriptor["narrative"], source_key=source["source_key"], chunk_hash_keys=hash_keys
        ),
    }
    runtime_design = (
        descriptor.get("runtime_design")
        or translated_manifest.get("runtime_design")
        or dict(dict(descriptor.get("source") or {}).get("metadata") or {}).get(
            "runtime_manifest"
        )
    )
    if runtime_design is not None:
        content["runtime_design"] = _translate_module_refs(
            runtime_design,
            source_key=source["source_key"],
            chunk_hash_keys=hash_keys,
        )
    package = build_content_package(
        kind="module",
        package_id=str(descriptor["id"]),
        version=str(descriptor["version"]),
        system_id=COC_SYSTEM_ID,
        manifest=translated_manifest,
        dependencies=[copy.deepcopy(dict(item)) for item in descriptor.get("dependencies") or []],
        sources=[source],
        assets=assets,
        content_reviews=reviews,
        actors=[copy.deepcopy(dict(actor)) for actor in descriptor.get("actors") or []],
        content=content,
        metadata=package_metadata,
    )
    return validate_coc_content_package(package), blobs
