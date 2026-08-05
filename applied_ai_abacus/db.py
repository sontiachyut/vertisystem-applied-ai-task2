from __future__ import annotations

from sqlalchemy import BIGINT, CheckConstraint, Column, MetaData, SmallInteger, Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


BIGINT_MIN = -(2**63)
BIGINT_MAX = 2**63 - 1

metadata = MetaData()

abacus_state = Table(
    "abacus_state",
    metadata,
    Column("state_id", SmallInteger, primary_key=True),
    Column("current_sum", BIGINT, nullable=False),
    CheckConstraint("state_id = 1", name="ck_abacus_state_singleton_row"),
)


def build_engine(database_url: str) -> Engine:
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False, "timeout": 30}
    return create_engine(
        database_url,
        future=True,
        connect_args=connect_args,
        pool_pre_ping=not database_url.startswith("sqlite"),
    )


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
