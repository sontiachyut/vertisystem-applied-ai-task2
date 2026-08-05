from __future__ import annotations

from dataclasses import dataclass

from .repository import AbacusRepository


@dataclass
class AbacusService:
    repository: AbacusRepository

    def bootstrap(self) -> None:
        self.repository.bootstrap()

    def add_number(self, number: int) -> int:
        return self.repository.add_number(number)

    def get_sum(self) -> int:
        return self.repository.get_sum()

    def reset_sum(self) -> int:
        return self.repository.reset_sum()
