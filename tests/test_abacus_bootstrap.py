from __future__ import annotations

from types import SimpleNamespace

from applied_ai_abacus.repository import AbacusRepository, POSTGRES_BOOTSTRAP_LOCK_KEY


class _RecordingSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict | None]] = []

    def execute(self, statement, params: dict | None = None) -> None:
        self.calls.append((str(statement), params))


class _RecordingSessionFactory:
    def __init__(self, session: _RecordingSession) -> None:
        self.session = session

    def begin(self) -> "_RecordingSessionFactory":
        return self

    def __enter__(self) -> _RecordingSession:
        return self.session

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_postgresql_bootstrap_takes_advisory_lock_before_schema_setup() -> None:
    session = _RecordingSession()
    repository = AbacusRepository(
        engine=SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        session_factory=_RecordingSessionFactory(session),
    )

    repository.bootstrap()

    assert len(session.calls) == 3
    assert "pg_advisory_xact_lock" in session.calls[0][0]
    assert session.calls[0][1] == {"lock_key": POSTGRES_BOOTSTRAP_LOCK_KEY}
    assert "CREATE TABLE IF NOT EXISTS abacus_state" in session.calls[1][0]
    assert "INSERT INTO abacus_state" in session.calls[2][0]


def test_non_postgresql_bootstrap_skips_advisory_lock() -> None:
    session = _RecordingSession()
    repository = AbacusRepository(
        engine=SimpleNamespace(dialect=SimpleNamespace(name="sqlite")),
        session_factory=_RecordingSessionFactory(session),
    )

    repository.bootstrap()

    assert len(session.calls) == 2
    assert "CREATE TABLE IF NOT EXISTS abacus_state" in session.calls[0][0]
    assert "INSERT INTO abacus_state" in session.calls[1][0]
