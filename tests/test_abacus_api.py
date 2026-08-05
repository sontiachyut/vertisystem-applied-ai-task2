from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from applied_ai_abacus.app import create_app


@pytest.fixture
def abacus_db_url(tmp_path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'abacus.db'}"


def test_get_sum_starts_at_zero(abacus_db_url: str) -> None:
    with TestClient(create_app(database_url=abacus_db_url)) as client:
        response = client.get("/abacus/sum")

    assert response.status_code == 200
    assert response.json() == {"sum": 0}


def test_post_number_increments_sum(abacus_db_url: str) -> None:
    with TestClient(create_app(database_url=abacus_db_url)) as client:
        post_response = client.post("/abacus/number", json={"number": 7})
        get_response = client.get("/abacus/sum")

    assert post_response.status_code == 200
    assert post_response.json() == {"sum": 7}
    assert get_response.status_code == 200
    assert get_response.json() == {"sum": 7}


def test_multiple_posts_accumulate_correctly(abacus_db_url: str) -> None:
    with TestClient(create_app(database_url=abacus_db_url)) as client:
        client.post("/abacus/number", json={"number": 4})
        client.post("/abacus/number", json={"number": 9})
        client.post("/abacus/number", json={"number": -3})
        response = client.get("/abacus/sum")

    assert response.status_code == 200
    assert response.json() == {"sum": 10}


def test_delete_resets_sum_to_zero(abacus_db_url: str) -> None:
    with TestClient(create_app(database_url=abacus_db_url)) as client:
        client.post("/abacus/number", json={"number": 19})
        delete_response = client.delete("/abacus/sum")
        get_response = client.get("/abacus/sum")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"sum": 0}
    assert get_response.status_code == 200
    assert get_response.json() == {"sum": 0}


def test_invalid_string_payload_is_rejected_without_state_change(abacus_db_url: str) -> None:
    with TestClient(create_app(database_url=abacus_db_url)) as client:
        client.post("/abacus/number", json={"number": 11})
        invalid_response = client.post("/abacus/number", json={"number": "abc"})
        get_response = client.get("/abacus/sum")

    assert invalid_response.status_code == 422
    assert get_response.status_code == 200
    assert get_response.json() == {"sum": 11}


def test_boolean_payload_is_rejected_without_state_change(abacus_db_url: str) -> None:
    with TestClient(create_app(database_url=abacus_db_url)) as client:
        client.post("/abacus/number", json={"number": 11})
        invalid_response = client.post("/abacus/number", json={"number": True})
        get_response = client.get("/abacus/sum")

    assert invalid_response.status_code == 422
    assert get_response.status_code == 200
    assert get_response.json() == {"sum": 11}


def test_overflowing_write_returns_conflict_and_preserves_sum(abacus_db_url: str) -> None:
    with TestClient(create_app(database_url=abacus_db_url)) as client:
        max_response = client.post("/abacus/number", json={"number": 9223372036854775807})
        overflow_response = client.post("/abacus/number", json={"number": 1})
        get_response = client.get("/abacus/sum")

    assert max_response.status_code == 200
    assert max_response.json() == {"sum": 9223372036854775807}
    assert overflow_response.status_code == 409
    assert get_response.status_code == 200
    assert get_response.json() == {"sum": 9223372036854775807}


def test_two_nodes_share_the_same_committed_sum(abacus_db_url: str) -> None:
    node_a_app = create_app(database_url=abacus_db_url)
    node_b_app = create_app(database_url=abacus_db_url)

    with TestClient(node_a_app) as node_a, TestClient(node_b_app) as node_b:
        post_response = node_a.post("/abacus/number", json={"number": 5})
        get_response = node_b.get("/abacus/sum")

    assert post_response.status_code == 200
    assert post_response.json() == {"sum": 5}
    assert get_response.status_code == 200
    assert get_response.json() == {"sum": 5}


def test_reset_on_one_node_is_visible_on_another(abacus_db_url: str) -> None:
    node_a_app = create_app(database_url=abacus_db_url)
    node_b_app = create_app(database_url=abacus_db_url)

    with TestClient(node_a_app) as node_a, TestClient(node_b_app) as node_b:
        node_a.post("/abacus/number", json={"number": 14})
        delete_response = node_b.delete("/abacus/sum")
        get_response = node_a.get("/abacus/sum")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"sum": 0}
    assert get_response.status_code == 200
    assert get_response.json() == {"sum": 0}
