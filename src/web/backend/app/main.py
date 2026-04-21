from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import get_influx_service
from app.api.routes import router
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend service for EcoRetrofit telemetry and savings analytics.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {
            "status": "online",
            "docs": "/docs",
        }

    @app.on_event("shutdown")
    def shutdown_handler() -> None:
        get_influx_service().close()

    app.include_router(router, prefix=settings.api_prefix)
    return app
