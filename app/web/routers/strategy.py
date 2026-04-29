# -*- coding: utf-8 -*-

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import init
from app.web.utils import read_yaml, validate_regex, write_yaml

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


class StrategyRule(BaseModel):
    site: str
    section_name: str
    name: str
    pattern: str
    save_path: str | None = ""


class StrategyTestRequest(BaseModel):
    pattern: str
    title: str


def _load_flat(data: dict) -> list[dict]:
    """将嵌套结构 {site: {section: [rule]}} 展平为带 id 的列表"""
    flat = []
    for site, sections in data.items():
        if not isinstance(sections, dict):
            continue
        for section_name, rules in sections.items():
            if not isinstance(rules, list):
                continue
            for rule in rules:
                flat.append({
                    "site": site,
                    "section_name": section_name,
                    "name": rule.get("name", ""),
                    "pattern": rule.get("pattern", ""),
                    "save_path": rule.get("save_path") or "",
                })
    return flat


def _flat_to_nested(flat: list[dict]) -> dict:
    """将展平列表重新组装为嵌套结构"""
    data: dict = {}
    for rule in flat:
        site = rule["site"]
        section = rule["section_name"]
        data.setdefault(site, {}).setdefault(section, []).append({
            "name": rule["name"],
            "pattern": rule["pattern"],
            "save_path": rule["save_path"] or "",
        })
    return data


def _normalize(rule: StrategyRule) -> dict:
    site = rule.site.strip()
    section_name = rule.section_name.strip()
    name = rule.name.strip()
    pattern = rule.pattern.strip()
    save_path = (rule.save_path or "").strip()
    if save_path and not save_path.startswith("/"):
        save_path = f"/{save_path}"
    if not site or not section_name or not name or not pattern:
        raise HTTPException(status_code=400, detail="site, section_name, name and pattern are required")
    return {"site": site, "section_name": section_name, "name": name, "pattern": pattern, "save_path": save_path}


@router.get("/rules")
def list_rules():
    data = read_yaml(init.STRATEGY_FILE)
    flat = _load_flat(data)
    return {"items": [{**rule, "id": idx} for idx, rule in enumerate(flat)]}


@router.post("/rules")
def create_rule(rule: StrategyRule):
    normalized = _normalize(rule)
    validate_regex(normalized["pattern"])
    data = read_yaml(init.STRATEGY_FILE)
    flat = _load_flat(data)
    flat.append(normalized)
    write_yaml(init.STRATEGY_FILE, _flat_to_nested(flat))
    return {"ok": True, "id": len(flat) - 1}


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, rule: StrategyRule):
    normalized = _normalize(rule)
    validate_regex(normalized["pattern"])
    data = read_yaml(init.STRATEGY_FILE)
    flat = _load_flat(data)
    if rule_id < 0 or rule_id >= len(flat):
        raise HTTPException(status_code=404, detail="Strategy rule not found")
    flat[rule_id] = normalized
    write_yaml(init.STRATEGY_FILE, _flat_to_nested(flat))
    return {"ok": True}


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int):
    data = read_yaml(init.STRATEGY_FILE)
    flat = _load_flat(data)
    if rule_id < 0 or rule_id >= len(flat):
        raise HTTPException(status_code=404, detail="Strategy rule not found")
    deleted = flat.pop(rule_id)
    write_yaml(init.STRATEGY_FILE, _flat_to_nested(flat))
    return {"ok": True, "deleted": deleted}


@router.post("/test")
def test_rule(payload: StrategyTestRequest):
    validate_regex(payload.pattern)
    matched = re.search(payload.pattern, payload.title, re.IGNORECASE) is not None
    return {"matched": matched}
