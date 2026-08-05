"""Tests for the football-data.org client — all HTTP mocked with respx."""

import logging
import time

import httpx
import pytest
import respx

from ingestion.client import (
    BASE_URL,
    FootballDataClient,
    MissingAPIKeyError,
    RateLimitedError,
    count_matches,
    count_scorers,
    count_standings_rows,
)

MATCHES_URL = f"{BASE_URL}/competitions/WC/matches"
STANDINGS_URL = f"{BASE_URL}/competitions/WC/standings"
SCORERS_URL = f"{BASE_URL}/competitions/WC/scorers"

MATCHES_PAYLOAD = {
    "competition": {"code": "WC"},
    "matches": [
        {"id": 1, "status": "FINISHED", "score": {"fullTime": {"home": 2, "away": 0}}},
        {"id": 2, "status": "SCHEDULED", "score": {"fullTime": {"home": None, "away": None}}},
    ],
}

STANDINGS_PAYLOAD = {
    "competition": {"code": "WC"},
    "standings": [
        {"group": "GROUP_A", "table": [{"position": 1}, {"position": 2}]},
        {"group": "GROUP_B", "table": [{"position": 1}]},
    ],
}


def make_client(**kwargs) -> FootballDataClient:
    """Client with no rate-limit wait and near-instant backoff for tests."""
    kwargs.setdefault("api_key", "test-key")
    kwargs.setdefault("min_interval_s", 0.0)
    kwargs.setdefault("backoff_base_s", 0.001)
    kwargs.setdefault("max_backoff_s", 0.01)
    return FootballDataClient(**kwargs)


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("FOOTBALL_DATA_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError):
        FootballDataClient()


def test_api_key_read_from_environment(monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "env-key")
    with FootballDataClient() as client:
        assert client.api_key == "env-key"


@respx.mock
def test_fetch_matches_returns_payload_and_logs_row_count(caplog):
    route = respx.get(MATCHES_URL, headers={"X-Auth-Token": "test-key"}).mock(
        return_value=httpx.Response(200, json=MATCHES_PAYLOAD)
    )
    with make_client() as client, caplog.at_level(logging.INFO, logger="ingestion.client"):
        payload = client.fetch_matches()
    assert route.called
    assert payload == MATCHES_PAYLOAD
    assert count_matches(payload) == 2
    assert "2 match rows" in caplog.text


@respx.mock
def test_fetch_standings_returns_payload_and_logs_row_count(caplog):
    respx.get(STANDINGS_URL).mock(return_value=httpx.Response(200, json=STANDINGS_PAYLOAD))
    with make_client() as client, caplog.at_level(logging.INFO, logger="ingestion.client"):
        payload = client.fetch_standings()
    assert payload == STANDINGS_PAYLOAD
    assert count_standings_rows(payload) == 3
    assert "3 standings rows" in caplog.text


@respx.mock
def test_fetch_scorers_returns_payload_and_logs_row_count(caplog):
    payload = {
        "scorers": [{"player": {"name": "X"}, "goals": 5}, {"player": {"name": "Y"}, "goals": 3}]
    }
    route = respx.get(SCORERS_URL).mock(return_value=httpx.Response(200, json=payload))
    with make_client() as client, caplog.at_level(logging.INFO, logger="ingestion.client"):
        result = client.fetch_scorers()
    assert result == payload
    assert count_scorers(result) == 2
    assert route.calls.last.request.url.params["limit"] == "30"
    assert "2 scorer rows" in caplog.text


@respx.mock
def test_retry_on_429_respects_retry_after_then_succeeds():
    route = respx.get(MATCHES_URL).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json=MATCHES_PAYLOAD),
        ]
    )
    with make_client() as client:
        payload = client.fetch_matches()
    assert route.call_count == 2
    assert count_matches(payload) == 2


@respx.mock
def test_retry_on_server_error_then_succeeds():
    route = respx.get(MATCHES_URL).mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(503),
            httpx.Response(200, json=MATCHES_PAYLOAD),
        ]
    )
    with make_client() as client:
        payload = client.fetch_matches()
    assert route.call_count == 3
    assert payload == MATCHES_PAYLOAD


@respx.mock
def test_retry_on_network_error_then_succeeds():
    route = respx.get(STANDINGS_URL).mock(
        side_effect=[
            httpx.ConnectTimeout("boom"),
            httpx.Response(200, json=STANDINGS_PAYLOAD),
        ]
    )
    with make_client() as client:
        payload = client.fetch_standings()
    assert route.call_count == 2
    assert payload == STANDINGS_PAYLOAD


@respx.mock
def test_client_error_fails_fast_without_retry():
    route = respx.get(MATCHES_URL).mock(return_value=httpx.Response(403))
    with make_client() as client, pytest.raises(httpx.HTTPStatusError):
        client.fetch_matches()
    assert route.call_count == 1  # 4xx (except 429) must never be retried


@respx.mock
def test_persistent_429_gives_up_after_max_attempts():
    route = respx.get(MATCHES_URL).mock(
        return_value=httpx.Response(429, headers={"Retry-After": "0"})
    )
    with make_client() as client, pytest.raises(RateLimitedError):
        client.fetch_matches()
    assert route.call_count == 5  # MAX_ATTEMPTS


@respx.mock
def test_exhausted_minute_quota_header_defers_next_request():
    respx.get(MATCHES_URL).mock(
        return_value=httpx.Response(
            200,
            json=MATCHES_PAYLOAD,
            headers={"X-Requests-Available-Minute": "0", "X-RequestCounter-Reset": "0.2"},
        )
    )
    with make_client() as client:
        client.fetch_matches()
        start = time.monotonic()
        client.fetch_matches()
        elapsed = time.monotonic() - start
    assert elapsed >= 0.15  # deferred until the server-announced counter reset


@respx.mock
def test_remaining_quota_does_not_throttle():
    respx.get(MATCHES_URL).mock(
        return_value=httpx.Response(
            200,
            json=MATCHES_PAYLOAD,
            headers={"X-Requests-Available-Minute": "7", "X-RequestCounter-Reset": "42"},
        )
    )
    with make_client() as client:
        start = time.monotonic()
        client.fetch_matches()
        client.fetch_matches()
        elapsed = time.monotonic() - start
    assert elapsed < 0.1


@respx.mock
def test_rate_limit_spaces_out_consecutive_requests():
    respx.get(MATCHES_URL).mock(return_value=httpx.Response(200, json=MATCHES_PAYLOAD))
    with make_client(min_interval_s=0.2) as client:
        start = time.monotonic()
        client.fetch_matches()
        client.fetch_matches()
        elapsed = time.monotonic() - start
    assert elapsed >= 0.2
