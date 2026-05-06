# -*- coding: utf-8 -*-

import re

from fastapi import APIRouter
from pydantic import BaseModel

from app.web.utils import validate_regex

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


class StrategyTestRequest(BaseModel):
    pattern: str
    title: str


@router.post("/test")
def test_rule(payload: StrategyTestRequest):
    validate_regex(payload.pattern)
    matched = re.search(payload.pattern, payload.title, re.IGNORECASE) is not None
    return {"matched": matched}
