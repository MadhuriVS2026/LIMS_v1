"""
FastAPI application entry point — Anti Gravity LIMS (Enterprise Clean Architecture).
Configures middleware, routers, CORS, and OpenAPI documentation.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from src.api.middleware.correlation_id import CorrelationIdMiddleware
from src.api.middleware.exception_handler import ExceptionHandlerMiddleware
from src.api.middleware.request_logging import RequestLoggingMiddleware
from src.api.v1.router import api_v1_router
from src.config.logging_config import configure_file_logging
from src.config.settings import settings
from src.infrastructure.database.session import init_models
from src.observability.structured_logger import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    configure_logging()
    configure_file_logging()
    await init_models()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Anti Gravity LIMS — Enterprise Clean Architecture (FastAPI + React)",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title, version=app.version, description=app.description, routes=app.routes,
    )
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["OAuth2PasswordBearer"] = {
        "type": "oauth2",
        "flows": {"password": {"tokenUrl": "api/v1/auth/login", "scopes": {}}},
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# ─── Middleware (order matters: outermost first) ───
app.add_middleware(ExceptionHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ───
app.include_router(api_v1_router)


@app.get("/", tags=["Root"])
async def root() -> dict:
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"}
