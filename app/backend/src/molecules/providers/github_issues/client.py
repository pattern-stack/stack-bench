"""GitHub REST API client."""

from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Any

import httpx


class GitHubClientError(Exception):
    """Base error for GitHub client operations."""


class GitHubAuthError(GitHubClientError):
    """Authentication failure."""


class GitHubRateLimitError(GitHubClientError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(message)


class GitHubAPIError(GitHubClientError):
    """HTTP error from GitHub API."""

    def __init__(self, message: str, status_code: int = 0) -> None:
        self.status_code = status_code
        super().__init__(message)


class GitHubClient:
    """Async client for GitHub REST API.

    Features:
        - Token auth (constructor or GITHUB_TOKEN env var)
        - Rate limit handling (X-RateLimit headers)
        - Link header pagination
        - Retry with exponential backoff
    """

    API_URL = "https://api.github.com"
    MAX_RETRIES = 3
    BASE_BACKOFF = 1.0

    def __init__(self, token: str | None = None, base_url: str | None = None) -> None:
        self._token = token or os.environ.get("GITHUB_TOKEN")
        if not self._token:
            raise GitHubAuthError("No token. Pass token or set GITHUB_TOKEN env var.")
        self._base_url = (base_url or self.API_URL).rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> GitHubClient:
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Send a GET request."""
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Send a POST request."""
        return await self._request("POST", path, json=json)

    async def patch(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Send a PATCH request."""
        return await self._request("PATCH", path, json=json)

    async def delete(self, path: str) -> None:
        """Send a DELETE request."""
        await self._request("DELETE", path)

    async def get_paginated(self, path: str, params: dict[str, Any] | None = None) -> list[Any]:
        """Fetch all pages of a paginated endpoint."""
        all_items: list[Any] = []
        params = dict(params or {})
        params.setdefault("per_page", 100)
        url: str | None = f"{self._base_url}{path}"

        while url:
            response = await self._request_raw("GET", url, params=params)
            data = response.json()
            if isinstance(data, list):
                all_items.extend(data)
            else:
                all_items.append(data)

            # Parse Link header for next page
            url = self._parse_next_link(response.headers.get("Link", ""))
            params = {}  # params already encoded in URL for subsequent pages

        return all_items

    def _parse_next_link(self, link_header: str) -> str | None:
        """Extract next page URL from Link header."""
        if not link_header:
            return None
        for part in link_header.split(","):
            match = re.match(r'\s*<([^>]+)>\s*;\s*rel="next"', part.strip())
            if match:
                return match.group(1)
        return None

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self._base_url}{path}" if not path.startswith("http") else path
        response = await self._request_raw(method, url, **kwargs)
        if response.status_code == 204:
            return None
        return response.json()

    async def _request_raw(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        if not self._client:
            raise GitHubClientError("Client not initialized. Use 'async with GitHubClient() as client:'")

        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self._client.request(method, url, **kwargs)

                # Rate limiting via X-RateLimit headers
                if response.status_code == 403:
                    remaining = response.headers.get("X-RateLimit-Remaining", "1")
                    if remaining == "0":
                        reset_at = int(response.headers.get("X-RateLimit-Reset", "0"))
                        retry_after = max(reset_at - int(time.time()), 1)
                        if attempt < self.MAX_RETRIES - 1:
                            await asyncio.sleep(min(retry_after, 60))
                            continue
                        raise GitHubRateLimitError("Rate limited", retry_after=float(retry_after))

                # Rate limiting via Retry-After header
                if response.status_code == 429:
                    retry_after_val = float(response.headers.get("Retry-After", self.BASE_BACKOFF * (2**attempt)))
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(retry_after_val)
                        continue
                    raise GitHubRateLimitError(
                        f"Rate limited after {self.MAX_RETRIES} retries",
                        retry_after=retry_after_val,
                    )

                if response.status_code == 401:
                    raise GitHubAuthError("Authentication failed. Check your token.")

                if response.status_code == 404:
                    raise GitHubAPIError(f"Not found: {url}", status_code=404)

                if response.status_code >= 400:
                    raise GitHubAPIError(
                        f"HTTP {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    )

                return response

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.BASE_BACKOFF * (2**attempt))
                    continue
                raise GitHubClientError(f"Network error: {e}") from e

        raise GitHubClientError(f"Failed after {self.MAX_RETRIES} retries") from last_error
