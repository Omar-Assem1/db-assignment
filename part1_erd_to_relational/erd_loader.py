
from __future__ import annotations

import json

from models import Attribute, Entity, Relationship

_CARD_ALIASES = {"N:M": "M:N", "N:N": "M:N", "M:M": "M:N", "1:M": "1:N", "M:1": "N:1"}
_VALID_CARD = {"1:1", "1:N", "N:1", "M:N"}
_VALID_PART = {"total", "partial"}


def load_erd(path: str):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return parse_erd(data)


def parse_erd(data: dict):

    if not isinstance(data, dict) or not isinstance(data.get("entities"), list):
        raise ValueError("ERD JSON must be an object with an 'entities' list")

    entities = [_parse_entity(e) for e in data["entities"]]
    names = [e.name for e in entities]
    dups = {n for n in names if names.count(n) > 1}
    if dups:
        raise ValueError(f"Duplicate entity names: {sorted(dups)}")
    by_name = {e.name: e for e in entities}

    for e in entities:
        if e.is_weak:
            if not e.owner or e.owner not in by_name:
                raise ValueError(f"Weak entity '{e.name}' needs a valid 'owner' entity")
        elif not any(a.is_primary_key for a in e.attributes):
            raise ValueError(f"Strong entity '{e.name}' has no primary key")

    relationships = [_parse_relationship(r, by_name) for r in data.get("relationships", [])]
    return entities, relationships


def _parse_attribute(raw: dict, where: str) -> Attribute:
    if not isinstance(raw, dict) or "name" not in raw:
        raise ValueError(f"Attribute without a 'name' in {where}")
    attr = Attribute(
        name=raw["name"],
        is_primary_key=bool(raw.get("isPrimaryKey", False)),
        is_partial_key=bool(raw.get("isPartialKey", False)),
        is_multi_valued=bool(raw.get("isMultiValued", False)),
        composite=list(raw.get("composite", [])),
    )
    if attr.is_primary_key and attr.is_multi_valued:
        raise ValueError(f"Key attribute '{attr.name}' in {where} cannot be multi-valued")
    return attr


def _parse_entity(raw: dict) -> Entity:
    if not isinstance(raw, dict) or "name" not in raw:
        raise ValueError("Every entity needs a 'name'")
    where = f"entity '{raw['name']}'"
    return Entity(
        name=raw["name"],
        attributes=[_parse_attribute(a, where) for a in raw.get("attributes", [])],
        is_weak=bool(raw.get("isWeak", False)),
        owner=raw.get("owner"),
    )


def _parse_relationship(raw: dict, entities: dict) -> Relationship:
    for key in ("name", "entity1", "entity2", "cardinality"):
        if key not in raw:
            raise ValueError(f"Relationship is missing '{key}': {raw}")
    for key in ("entity1", "entity2"):
        if raw[key] not in entities:
            raise ValueError(f"Relationship '{raw['name']}' references unknown entity '{raw[key]}'")

    card = str(raw["cardinality"]).strip().upper()
    card = _CARD_ALIASES.get(card, card)
    if card not in _VALID_CARD:
        raise ValueError(f"Relationship '{raw['name']}': invalid cardinality '{raw['cardinality']}'")

    part = [p.lower() for p in raw.get("participation", ["partial", "partial"])]
    if len(part) != 2 or any(p not in _VALID_PART for p in part):
        raise ValueError(f"Relationship '{raw['name']}': 'participation' must be two of total/partial")

    where = f"relationship '{raw['name']}'"
    return Relationship(
        name=raw["name"],
        entity1=raw["entity1"],
        entity2=raw["entity2"],
        cardinality=card,
        attributes=[_parse_attribute(a, where) for a in raw.get("attributes", [])],
        participation1=part[0],
        participation2=part[1],
    )