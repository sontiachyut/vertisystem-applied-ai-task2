from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
import threading

import pytest

from applied_ai_abacus.db import build_engine, build_session_factory
from applied_ai_abacus.repository import AbacusRepository
from applied_ai_abacus.service import AbacusService


@pytest.fixture
def abacus_db_url(tmp_path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'abacus.db'}"


def test_many_concurrent_posts_do_not_lose_updates_on_one_node(abacus_db_url: str) -> None:
    service, cleanup = _build_service(abacus_db_url)
    try:
        with ThreadPoolExecutor(max_workers=16) as executor:
            results = list(executor.map(lambda _: service.add_number(1), range(100)))

        assert len(results) == 100
        assert service.get_sum() == 100
    finally:
        cleanup()


def test_many_concurrent_posts_do_not_lose_updates_across_two_nodes(abacus_db_url: str) -> None:
    node_a, cleanup_a = _build_service(abacus_db_url)
    node_b, cleanup_b = _build_service(abacus_db_url)
    try:
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [
                executor.submit((node_a if index % 2 == 0 else node_b).add_number, 1)
                for index in range(100)
            ]
            results = [future.result() for future in futures]

        assert len(results) == 100
        assert node_a.get_sum() == 100
        assert node_b.get_sum() == 100
    finally:
        cleanup_b()
        cleanup_a()


def test_concurrent_reset_and_add_serialize_to_a_valid_final_total(abacus_db_url: str) -> None:
    node_a, cleanup_a = _build_service(abacus_db_url)
    node_b, cleanup_b = _build_service(abacus_db_url)
    barrier = threading.Barrier(2)

    try:
        node_a.add_number(10)

        def add_number() -> int:
            barrier.wait()
            return node_a.add_number(5)

        def reset_sum() -> int:
            barrier.wait()
            return node_b.reset_sum()

        with ThreadPoolExecutor(max_workers=2) as executor:
            add_future = executor.submit(add_number)
            reset_future = executor.submit(reset_sum)
            add_future.result()
            reset_future.result()

        assert node_a.get_sum() in {0, 5}
        assert node_b.get_sum() in {0, 5}
        assert node_a.get_sum() == node_b.get_sum()
    finally:
        cleanup_b()
        cleanup_a()


def test_concurrent_bootstrap_is_idempotent_across_two_nodes(abacus_db_url: str) -> None:
    engine_a = build_engine(abacus_db_url)
    engine_b = build_engine(abacus_db_url)
    node_a = AbacusService(repository=AbacusRepository(engine=engine_a, session_factory=build_session_factory(engine_a)))
    node_b = AbacusService(repository=AbacusRepository(engine=engine_b, session_factory=build_session_factory(engine_b)))

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(node.bootstrap) for node in (node_a, node_b)]
            for future in futures:
                future.result()

        assert node_a.get_sum() == 0
        assert node_b.get_sum() == 0
    finally:
        engine_b.dispose()
        engine_a.dispose()


def _build_service(database_url: str) -> tuple[AbacusService, Callable[[], None]]:
    engine = build_engine(database_url)
    repository = AbacusRepository(engine=engine, session_factory=build_session_factory(engine))
    service = AbacusService(repository=repository)
    service.bootstrap()

    def cleanup() -> None:
        engine.dispose()

    return service, cleanup
