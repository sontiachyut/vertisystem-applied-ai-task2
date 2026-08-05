from __future__ import annotations

from dataclasses import dataclass
import os


DEFAULT_DATABASE_URL = "postgresql+psycopg://abacus:abacus@127.0.0.1:5432/abacus"


@dataclass(frozen=True)
class AbacusSettings:
    database_url: str = DEFAULT_DATABASE_URL

    @classmethod
    def from_env(cls, *, database_url: str | None = None) -> "AbacusSettings":
        resolved_database_url = (database_url or os.getenv("ABACUS_DATABASE_URL", DEFAULT_DATABASE_URL)).strip()
        if not resolved_database_url:
            raise ValueError("ABACUS_DATABASE_URL must not be empty.")
        return cls(database_url=resolved_database_url)
