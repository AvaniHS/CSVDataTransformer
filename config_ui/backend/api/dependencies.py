"""FastAPI dependencies."""

from __future__ import annotations

from functools import lru_cache

from config_ui.backend.domain.session_service import SessionService
from config_ui.backend.settings import Settings
from config_ui.backend.storage.session_store import SessionStore


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def get_store() -> SessionStore:
    return SessionStore(get_settings())


def get_session_service() -> SessionService:
    return SessionService(get_store())
