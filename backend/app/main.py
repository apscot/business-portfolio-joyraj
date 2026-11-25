"""App factory and router wiring."""
import importlib
from types import ModuleType

from fastapi import FastAPI

from app.db import Base, engine

ROUTERS = ("auth", "investments", "trades", "pnl", "targets")


def _load(module: str) -> ModuleType | None:
    """Import an app module; return None only if that module itself does not exist yet."""
    try:
        return importlib.import_module(module)
    except ModuleNotFoundError as exc:
        if exc.name is None or not (module == exc.name or module.startswith(exc.name + ".")):
            raise
        return None


def create_app() -> FastAPI:
    app = FastAPI(title="F&O Portfolio Tracker")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for name in ROUTERS:
        mod = _load(f"app.routers.{name}")
        if mod is not None:
            app.include_router(mod.router)
    return app


_load("app.models")  # register tables on Base before create_all
Base.metadata.create_all(engine)
app = create_app()
