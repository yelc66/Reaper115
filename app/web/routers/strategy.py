# -*- coding: utf-8 -*-

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import init
from app.web.utils import read_yaml, validate_regex, write_yaml

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


class StrategyRule(BaseModel):
    section_name: str
    strategy_name: str
    pattern: str
    specify_save_path: str | None = ""


class StrategyTestRequest(BaseModel):
    pattern: str
    title: str


def _load_rules():
    data = read_yaml(init.STRATEGY_FILE)
    rules = data.get("title_regular") or []
    return data, rules


def _normalize_rule(rule: StrategyRule):
    normalized = {
        "section_name": rule.section_name.strip(),
        "strategy_name": rule.strategy_name.strip(),
        "pattern": rule.pattern.strip(),
        "specify_save_path": (rule.specify_save_path or "").strip(),
    }
    if normalized["specify_save_path"] and not normalized["specify_save_path"].startswith("/"):
        normalized["specify_save_path"] = f"/{normalized['specify_save_path']}"
    if not normalized["section_name"] or not normalized["strategy_name"] or not normalized["pattern"]:
        raise HTTPException(status_code=400, detail="section_name, strategy_name and pattern are required")
    return normalized


@router.get("/rules")
def list_rules():
    _, rules = _load_rules()
    return {"items": [{**rule, "id": index} for index, rule in enumerate(rules)]}


@router.post("/rules")
def create_rule(rule: StrategyRule):
    normalized_rule = _normalize_rule(rule)
    validate_regex(normalized_rule["pattern"])
    data, rules = _load_rules()
    rules.append(normalized_rule)
    data["title_regular"] = rules
    write_yaml(init.STRATEGY_FILE, data)
    return {"ok": True, "id": len(rules) - 1}


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, rule: StrategyRule):
    normalized_rule = _normalize_rule(rule)
    validate_regex(normalized_rule["pattern"])
    data, rules = _load_rules()
    if rule_id < 0 or rule_id >= len(rules):
        raise HTTPException(status_code=404, detail="Strategy rule not found")
    rules[rule_id] = normalized_rule
    data["title_regular"] = rules
    write_yaml(init.STRATEGY_FILE, data)
    return {"ok": True}


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int):
    data, rules = _load_rules()
    if rule_id < 0 or rule_id >= len(rules):
        raise HTTPException(status_code=404, detail="Strategy rule not found")
    deleted = rules.pop(rule_id)
    data["title_regular"] = rules
    write_yaml(init.STRATEGY_FILE, data)
    return {"ok": True, "deleted": deleted}


@router.post("/test")
def test_rule(payload: StrategyTestRequest):
    validate_regex(payload.pattern)
    matched = re.search(payload.pattern, payload.title, re.IGNORECASE) is not None
    return {"matched": matched}
