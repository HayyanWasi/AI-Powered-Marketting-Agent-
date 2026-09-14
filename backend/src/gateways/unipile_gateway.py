"""Unipile Gateway for LinkedIn REST API integration.

Includes circuit breaker protection on every method: HTTP 429 (rate limit)
and 202 (checkpoint/security challenge) are detected and reported to the
breaker, which halts all further automation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

from src.config.settings import settings

if TYPE_CHECKING:
    from src.modules.linkedin.worker.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class UnipileGateway:
    """Async Gateway for Unipile LinkedIn REST API with circuit breaker."""

    def __init__(
        self,
        dsn: str | None = None,
        token: str | None = None,
        timeout_seconds: float = 15.0,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.dsn = (dsn or settings.unipile_dsn).rstrip("/")
        self.token = token or settings.unipile_token
        self.timeout = timeout_seconds
        self._circuit_breaker = circuit_breaker

    def _get_headers(self) -> dict[str, str]:
        return {
            "X-API-KEY": self.token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _check_breaker(self, method_name: str) -> bool:
        """Return True if the call is allowed; False if breaker is OPEN."""
        if self._circuit_breaker and not self._circuit_breaker.can_proceed():
            logger.warning("Circuit breaker OPEN — skipping %s", method_name)
            return False
        return True

    def _handle_response(self, res: httpx.Response, method_name: str) -> bool:
        """Check response for 429/202 and report to breaker.

        Returns True if the response is a success (2xx, not 202).
        """
        if res.status_code == 429:
            if self._circuit_breaker:
                self._circuit_breaker.record_failure(429)
            logger.warning("%s returned HTTP 429 (rate limited)", method_name)
            return False
        if res.status_code == 202:
            if self._circuit_breaker:
                self._circuit_breaker.record_failure(202)
            logger.warning("%s returned HTTP 202 (checkpoint/security challenge)", method_name)
            return False
        if res.status_code >= 400:
            if self._circuit_breaker:
                self._circuit_breaker.record_failure(res.status_code)
            logger.warning("%s returned HTTP %d: %s", method_name, res.status_code, res.text[:200])
            return False

        if self._circuit_breaker:
            self._circuit_breaker.record_success()
        return True

    # ── Existing Methods (with circuit breaker) ──────────────────────────

    async def list_accounts(self) -> list[dict[str, Any]]:
        """List all connected accounts in Unipile."""
        if not self._check_breaker("list_accounts"):
            return []
        url = f"{self.dsn}/api/v1/accounts"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers())
                if self._handle_response(res, "list_accounts") and res.status_code == 200:
                    data = res.json()
                    return data.get("items", []) if isinstance(data, dict) else data
                return []
            except Exception as e:
                logger.error("Unipile list_accounts error: %s", e)
                return []

    async def get_account(self, account_id: str) -> dict[str, Any] | None:
        """Get details for a specific connected account."""
        if not self._check_breaker("get_account"):
            return None
        url = f"{self.dsn}/api/v1/accounts/{account_id}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers())
                if self._handle_response(res, "get_account") and res.status_code == 200:
                    return res.json()
                return None
            except Exception as e:
                logger.error("Unipile get_account error: %s", e)
                return None

    async def visit_profile(self, account_id: str, linkedin_id: str) -> bool:
        """Visit a prospect's LinkedIn profile (triggers 'viewed profile' notification)."""
        if not self._check_breaker("visit_profile"):
            return False
        url = f"{self.dsn}/api/v1/users/{linkedin_id}"
        params = {"account_id": account_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers(), params=params)
                return self._handle_response(res, "visit_profile") and res.status_code == 200
            except Exception as e:
                logger.error("Unipile visit_profile error: %s", e)
                return False

    async def send_connection_request(
        self, account_id: str, linkedin_id: str, message: str
    ) -> str | None:
        """Send a LinkedIn connection request with custom hook message.

        Returns invite_id if successful, None otherwise.
        """
        if not self._check_breaker("send_connection_request"):
            return None
        url = f"{self.dsn}/api/v1/users/invite"
        payload = {
            "account_id": account_id,
            "provider_id": linkedin_id,
            "message": message[:300],  # LinkedIn max note length 300
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                if self._handle_response(res, "send_connection_request") and res.status_code in (
                    200,
                    201,
                ):
                    data = res.json()
                    return data.get("invite_id") or data.get("id") or "invite_sent"
                return None
            except Exception as e:
                logger.error("Unipile send_connection_request error: %s", e)
                return None

    async def withdraw_invitation(self, account_id: str, invite_id: str) -> bool:
        """Withdraw a pending connection request."""
        if not self._check_breaker("withdraw_invitation"):
            return False
        url = f"{self.dsn}/api/v1/users/invite/{invite_id}"
        params = {"account_id": account_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.delete(url, headers=self._get_headers(), params=params)
                return self._handle_response(res, "withdraw_invitation") and res.status_code in (
                    200,
                    204,
                )
            except Exception as e:
                logger.error("Unipile withdraw_invitation error: %s", e)
                return False

    async def send_message(self, account_id: str, chat_id: str, text: str) -> str | None:
        """Send a direct message to a connected contact."""
        if not self._check_breaker("send_message"):
            return None
        url = f"{self.dsn}/api/v1/messages"
        payload = {
            "account_id": account_id,
            "chat_id": chat_id,
            "text": text,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                if self._handle_response(res, "send_message") and res.status_code in (200, 201):
                    data = res.json()
                    return data.get("message_id") or data.get("id") or "msg_sent"
                return None
            except Exception as e:
                logger.error("Unipile send_message error: %s", e)
                return None

    async def create_post(self, account_id: str, text: str) -> str | None:
        """Publish a text post on the connected LinkedIn profile via multipart form-data."""
        if not self._check_breaker("create_post"):
            return None
        url = f"{self.dsn}/api/v1/posts"
        headers = {
            "X-API-KEY": self.token,
            "Accept": "application/json",
        }
        files = {
            "account_id": (None, account_id),
            "text": (None, text),
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                res = await client.post(url, headers=headers, files=files)
                logger.info(
                    "[UNIPILE CREATE_POST] Status: %s, Response: %s",
                    res.status_code,
                    res.text[:200],
                )
                if self._handle_response(res, "create_post") and res.status_code in (200, 201, 202):
                    data = res.json() if res.text else {}
                    return (
                        data.get("post_id")
                        or data.get("id")
                        or data.get("social_id")
                        or "post_published"
                    )
                logger.error(
                    "[UNIPILE CREATE_POST] Failed with status %s: %s", res.status_code, res.text
                )
                return None
            except Exception as e:
                logger.error("Unipile create_post error: %s", e)
                return None

    async def register_webhook(self, callback_url: str, events: list[str]) -> bool:
        """Register a webhook receiver with Unipile for real-time events."""
        if not self._check_breaker("register_webhook"):
            return False
        url = f"{self.dsn}/api/v1/webhooks"
        payload = {
            "url": callback_url,
            "events": events,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                return self._handle_response(res, "register_webhook") and res.status_code in (
                    200,
                    201,
                )
            except Exception as e:
                logger.error("Unipile register_webhook error: %s", e)
                return False

    async def check_relation(self, account_id: str, linkedin_id: str) -> bool:
        """Check if the account is connected to a specific LinkedIn user."""
        if not self._check_breaker("check_relation"):
            return False
        url = f"{self.dsn}/api/v1/users/{linkedin_id}/relation"
        params = {"account_id": account_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers(), params=params)
                if self._handle_response(res, "check_relation") and res.status_code == 200:
                    data = res.json()
                    return data.get("is_connected", False)
                return False
            except Exception as e:
                logger.error("Unipile check_relation error: %s", e)
                return False

    # ── New Methods for Scheduler Engine ──────────────────────────────────

    async def search_people(
        self, account_id: str, keywords: str, limit: int = 150
    ) -> list[dict[str, Any]]:
        """Search LinkedIn for people matching keywords.

        Step 1 of the two-step targeting pipeline.
        """
        if not self._check_breaker("search_people"):
            return []
        url = f"{self.dsn}/api/v1/linkedin/search"
        params = {
            "account_id": account_id,
            "category": "people",
            "keywords": keywords,
            "limit": str(limit),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers(), params=params)
                if self._handle_response(res, "search_people") and res.status_code == 200:
                    data = res.json()
                    return data.get("items", []) if isinstance(data, dict) else data
                return []
            except Exception as e:
                logger.error("Unipile search_people error: %s", e)
                return []

    async def get_user_posts(
        self, account_id: str, profile_id: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Fetch recent posts from a specific LinkedIn profile.

        Step 2 of the two-step targeting pipeline.
        """
        if not self._check_breaker("get_user_posts"):
            return []
        url = f"{self.dsn}/api/v1/posts"
        params = {
            "account_id": account_id,
            "author_id": profile_id,
            "limit": str(limit),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers(), params=params)
                if self._handle_response(res, "get_user_posts") and res.status_code == 200:
                    data = res.json()
                    return data.get("items", []) if isinstance(data, dict) else data
                return []
            except Exception as e:
                logger.error("Unipile get_user_posts error: %s", e)
                return []

    async def like_post(self, account_id: str, post_id: str) -> bool:
        """Like a post on LinkedIn."""
        if not self._check_breaker("like_post"):
            return False
        url = f"{self.dsn}/api/v1/posts/{post_id}/like"
        payload = {"account_id": account_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                return self._handle_response(res, "like_post") and res.status_code in (200, 201)
            except Exception as e:
                logger.error("Unipile like_post error: %s", e)
                return False

    async def comment_on_post(self, account_id: str, post_id: str, text: str) -> str | None:
        """Comment on a LinkedIn post."""
        if not self._check_breaker("comment_on_post"):
            return None
        url = f"{self.dsn}/api/v1/posts/{post_id}/comments"
        payload = {
            "account_id": account_id,
            "text": text,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                if self._handle_response(res, "comment_on_post") and res.status_code in (
                    200,
                    201,
                ):
                    data = res.json()
                    return data.get("comment_id") or data.get("id") or "comment_posted"
                return None
            except Exception as e:
                logger.error("Unipile comment_on_post error: %s", e)
                return None

    async def get_feed_posts(self, account_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent posts from the account's LinkedIn feed."""
        if not self._check_breaker("get_feed_posts"):
            return []
        url = f"{self.dsn}/api/v1/posts"
        params = {"account_id": account_id, "limit": str(limit)}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers(), params=params)
                if self._handle_response(res, "get_feed_posts") and res.status_code == 200:
                    data = res.json()
                    return data.get("items", []) if isinstance(data, dict) else data
                return []
            except Exception as e:
                logger.error("Unipile get_feed_posts error: %s", e)
                return []


# ── Gateway Factory ──────────────────────────────────────────────────────────


def get_unipile_gateway(
    circuit_breaker: CircuitBreaker | None = None,
) -> UnipileGateway:
    """Factory function for gateway dependency injection.

    If ``USE_MOCK_UNIPILE=true`` in settings, returns a MockUnipileGateway
    that makes zero real HTTP calls.  Otherwise returns the real gateway
    with circuit breaker integration.

    All components MUST use this factory — never instantiate UnipileGateway
    directly.
    """
    if settings.use_mock_unipile:
        from src.gateways.mock_unipile_gateway import MockUnipileGateway

        logger.warning("Using MOCK Unipile Gateway — no real API calls")
        return MockUnipileGateway()
    return UnipileGateway(circuit_breaker=circuit_breaker)
