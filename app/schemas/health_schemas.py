# app/schemas/health_schemas.py
from pydantic import BaseModel
from typing import Dict, Optional


class ComponentStatus(BaseModel):
    status: str
    detail: Optional[str] = None
    last_update: Optional[str] = None


class StatusObject(BaseModel):
    indicator: str
    description: str


class PageInfo(BaseModel):
    name: str
    url: str
    time: str


class HealthResponse(BaseModel):
    page: PageInfo
    status: StatusObject
    components: Dict[str, ComponentStatus]
