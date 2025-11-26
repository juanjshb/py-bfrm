# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_router_v1
from app.core.config import settings
from app.core.logging import setup_logging
from app.infra.db.session import init_db

limiter = Limiter(key_func=get_remote_address)


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Routers
    app.include_router(api_router_v1)

    @app.on_event("startup")
    async def on_startup() -> None:
        await init_db()

    @app.get("/")
    async def root():
        return {"service": settings.PROJECT_NAME, "status": "ok"}

    return app


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded", "error": str(exc)},
    )


app = create_app()
