"""HTTP client for the football-data.org v4 API.

Free tier constraints: 10 requests/minute, enforced here with a minimum
interval between requests so callers cannot accidentally exceed it.
Every fetch logs the number of rows received (non-negotiable project rule:
no silent row drops anywhere in the pipeline).
"""

import logging
import os
import time

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.football-data.org/v4"
WORLD_CUP_COMPETITION = "WC"
FREE_TIER_MIN_INTERVAL_S = 6.0  # 10 requests/minute
MAX_ATTEMPTS = 5


class FootballDataError(Exception):
    """Base error for football-data.org client failures."""


class MissingAPIKeyError(FootballDataError):
    """No API key provided nor found in the environment."""


class RateLimitedError(FootballDataError):
    """HTTP 429 — carries the server-requested wait, if any."""

    def __init__(self, message: str, retry_after_s: float | None = None):
        super().__init__(message)
        self.retry_after_s = retry_after_s


class ServerError(FootballDataError):
    """HTTP 5xx — transient upstream failure, retryable."""


def count_matches(payload: dict) -> int:
    return len(payload.get("matches", []))


def count_standings_rows(payload: dict) -> int:
    return sum(len(group.get("table", [])) for group in payload.get("standings", []))


def _wait_respecting_retry_after(retry_state) -> float:
    """Honor a 429 Retry-After header, otherwise exponential backoff."""
    client: FootballDataClient = retry_state.args[0]
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exc, RateLimitedError) and exc.retry_after_s is not None:
        return min(exc.retry_after_s, client.max_backoff_s)
    return wait_exponential(multiplier=client.backoff_base_s, max=client.max_backoff_s)(
        retry_state
    )


class FootballDataClient:
    """Thin client over the endpoints the pipeline needs.

    Usage:
        with FootballDataClient() as client:
            matches = client.fetch_matches()
            standings = client.fetch_standings()
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = BASE_URL,
        competition: str = WORLD_CUP_COMPETITION,
        min_interval_s: float = FREE_TIER_MIN_INTERVAL_S,
        backoff_base_s: float = 2.0,
        max_backoff_s: float = 60.0,
        timeout_s: float = 30.0,
    ):
        self.api_key = api_key or os.getenv("FOOTBALL_DATA_API_KEY")
        if not self.api_key:
            raise MissingAPIKeyError(
                "No API key: pass api_key or set FOOTBALL_DATA_API_KEY in the environment"
            )
        self.competition = competition
        self.min_interval_s = min_interval_s
        self.backoff_base_s = backoff_base_s
        self.max_backoff_s = max_backoff_s
        self._last_request_at: float | None = None
        self._throttle_until: float | None = None
        self._client = httpx.Client(
            base_url=base_url,
            headers={"X-Auth-Token": self.api_key},
            timeout=timeout_s,
        )

    def __enter__(self) -> "FootballDataClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _respect_rate_limit(self) -> None:
        now = time.monotonic()
        wait_until = now
        if self._last_request_at is not None:
            wait_until = max(wait_until, self._last_request_at + self.min_interval_s)
        if self._throttle_until is not None:
            wait_until = max(wait_until, self._throttle_until)
        remaining = wait_until - now
        if remaining > 0:
            logger.debug("rate limit: sleeping %.1fs", remaining)
            time.sleep(remaining)

    def _note_server_throttle(self, response: httpx.Response) -> None:
        """football-data.org reports the remaining minute quota in response
        headers; when it hits 0, defer the next request until the counter
        resets instead of blindly hitting the rate limiter."""
        available = response.headers.get("X-Requests-Available-Minute")
        if available is None:
            return
        try:
            if int(available) > 0:
                return
            reset_s = response.headers.get("X-RequestCounter-Reset")
            wait_s = float(reset_s) if reset_s is not None else self.min_interval_s
        except ValueError:
            return
        self._throttle_until = time.monotonic() + wait_s
        logger.warning("minute quota exhausted, next request deferred by %.0fs", wait_s)

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, RateLimitedError, ServerError)),
        stop=stop_after_attempt(MAX_ATTEMPTS),
        wait=_wait_respecting_retry_after,
        reraise=True,
    )
    def _get(self, path: str, params: dict | None = None) -> dict:
        self._respect_rate_limit()
        self._last_request_at = time.monotonic()
        response = self._client.get(path, params=params)
        self._note_server_throttle(response)
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitedError(
                f"429 on GET {path}",
                retry_after_s=float(retry_after) if retry_after is not None else None,
            )
        if response.status_code >= 500:
            raise ServerError(f"{response.status_code} on GET {path}")
        response.raise_for_status()  # remaining 4xx: not retryable, fail fast
        return response.json()

    def fetch_matches(self, **params) -> dict:
        """All World Cup matches — fixtures AND results (same endpoint, `status` field)."""
        path = f"/competitions/{self.competition}/matches"
        payload = self._get(path, params=params or None)
        logger.info("GET %s -> %d match rows", path, count_matches(payload))
        return payload

    def fetch_standings(self, **params) -> dict:
        """World Cup group standings."""
        path = f"/competitions/{self.competition}/standings"
        payload = self._get(path, params=params or None)
        logger.info("GET %s -> %d standings rows", path, count_standings_rows(payload))
        return payload
