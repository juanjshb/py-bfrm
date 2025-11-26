# app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.iso import router as iso_router
from app.api.v1.endpoints.auditoria import router as auditoria_router


api_router_v1 = APIRouter(prefix="/api/v1")

api_router_v1.include_router(health_router)
api_router_v1.include_router(iso_router)
api_router_v1.include_router(auditoria_router)
