from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .db import BIGINT_MAX, BIGINT_MIN, abacus_state


class SumOverflowError(ValueError):
    """Raised when an accepted integer would overflow the supported BIGINT sum range."""


class AbacusStateMissingError(RuntimeError):
    """Raised when the authoritative singleton state row is unexpectedly missing."""


@dataclass
class AbacusRepository:
    engine: Engine
    session_factory: sessionmaker[Session]

    def bootstrap(self) -> None:
        with self.session_factory.begin() as session:
            session.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS abacus_state (
                      state_id SMALLINT PRIMARY KEY CHECK (state_id = 1),
                      current_sum BIGINT NOT NULL
                    )
                    """
                )
            )
            session.execute(
                text(
                    """
                    INSERT INTO abacus_state (state_id, current_sum)
                    VALUES (1, 0)
                    ON CONFLICT(state_id) DO NOTHING
                    """
                )
            )

    def get_sum(self) -> int:
        with self.session_factory() as session:
            return self._get_sum_for_session(session)

    def add_number(self, number: int) -> int:
        lower_bound = max(BIGINT_MIN, BIGINT_MIN - number)
        upper_bound = min(BIGINT_MAX, BIGINT_MAX - number)

        with self.session_factory.begin() as session:
            updated_sum = session.execute(
                text(
                    """
                    UPDATE abacus_state
                    SET current_sum = current_sum + :number
                    WHERE state_id = 1
                      AND current_sum BETWEEN :lower_bound AND :upper_bound
                    RETURNING current_sum
                    """
                ),
                {
                    "number": number,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                },
            ).scalar_one_or_none()

            if updated_sum is not None:
                return int(updated_sum)

            current_sum = self._get_sum_for_session(session)
            raise SumOverflowError(
                f"Adding {number} would overflow the signed BIGINT range from current sum {current_sum}."
            )

    def reset_sum(self) -> int:
        with self.session_factory.begin() as session:
            reset_sum = session.execute(
                text(
                    """
                    UPDATE abacus_state
                    SET current_sum = 0
                    WHERE state_id = 1
                    RETURNING current_sum
                    """
                )
            ).scalar_one_or_none()
            if reset_sum is None:
                raise AbacusStateMissingError("The authoritative abacus state row is missing.")
            return int(reset_sum)

    def _get_sum_for_session(self, session: Session) -> int:
        current_sum = session.execute(
            select(abacus_state.c.current_sum).where(abacus_state.c.state_id == 1)
        ).scalar_one_or_none()
        if current_sum is None:
            raise AbacusStateMissingError("The authoritative abacus state row is missing.")
        return int(current_sum)
