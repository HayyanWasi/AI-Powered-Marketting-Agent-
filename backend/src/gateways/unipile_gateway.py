"""Unipile Gateway for LinkedIn REST API integration."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class UnipileGateway:
    """Async Gateway for Unipile LinkedIn REST API."""

    def __init__(
        self,
        dsn: str | None = None,
        token: str | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.dsn = (dsn or settings.unipile_dsn).rstrip("/")
        self.token = token or settings.unipile_token
        self.timeout = timeout_seconds

    def _get_headers(self) -> dict[str, str]:
        return {
            "X-API-KEY": self.token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def list_accounts(self) -> list[dict[str, Any]]:
        """List all connected accounts in Unipile."""
        url = f"{self.dsn}/api/v1/accounts"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    return data.get("items", []) if isinstance(data, dict) else data
                logger.warning("Unipile list_accounts returned status %d", res.status_code)
                return []
            except Exception as e:
                logger.error("Unipile list_accounts error: %s", e)
                return []

    async def get_account(self, account_id: str) -> dict[str, Any] | None:
        """Get details for a specific connected account."""
        url = f"{self.dsn}/api/v1/accounts/{account_id}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code == 200:
                    return res.json()
                return None
            except Exception as e:
                logger.error("Unipile get_account error: %s", e)
                return None

    async def visit_profile(self, account_id: str, linkedin_id: str) -> bool:
        """Visit a prospect's LinkedIn profile (triggers 'viewed profile' notification)."""
        url = f"{self.dsn}/api/v1/users/{linkedin_id}"
        params = {"account_id": account_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers(), params=params)
                return res.status_code == 200
            except Exception as e:
                logger.error("Unipile visit_profile error: %s", e)
                return False

    async def send_connection_request(
        self, account_id: str, linkedin_id: str, message: str
    ) -> str | None:
        """Send a LinkedIn connection request with custom hook message.

        Returns invite_id if successful, None otherwise.
        """
        url = f"{self.dsn}/api/v1/users/invite"
        payload = {
            "account_id": account_id,
            "provider_id": linkedin_id,
            "message": message[:300],  # LinkedIn max note length 300
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                if res.status_code in (200, 201):
                    data = res.json()
                    return data.get("invite_id") or data.get("id") or "invite_sent"
                logger.warning("Unipile send_connection_request status %d: %s", res.status_code, res.text)
                return None
            except Exception as e:
                logger.error("Unipile send_connection_request error: %s", e)
                return None

    async def withdraw_invitation(self, account_id: str, invite_id: str) -> bool:
        """Withdraw a pending connection request."""
        url = f"{self.dsn}/api/v1/users/invite/{invite_id}"
        params = {"account_id": account_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.delete(url, headers=self._get_headers(), params=params)
                return res.status_code in (200, 204)
            except Exception as e:
                logger.error("Unipile withdraw_invitation error: %s", e)
                return False

    async def send_message(self, account_id: str, chat_id: str, text: str) -> str | None:
        """Send a direct message to a connected contact."""
        url = f"{self.dsn}/api/v1/messages"
        payload = {
            "account_id": account_id,
            "chat_id": chat_id,
            "text": text,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                if res.status_code in (200, 201):
                    data = res.json()
                    return data.get("message_id") or data.get("id") or "msg_sent"
                return None
            except Exception as e:
                logger.error("Unipile send_message error: %s", e)
                return None

    async def create_post(self, account_id: str, text: str) -> str | None:
        """Publish a text post on the connected LinkedIn profile."""
        url = f"{self.dsn}/api/v1/posts"
        payload = {
            "account_id": account_id,
            "text": text,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                if res.status_code in (200, 201):
                    data = res.json()
                    return data.get("post_id") or data.get("id") or "post_published"
                logger.warning("Unipile create_post status %d: %s", res.status_code, res.text)
                return None
            except Exception as e:
                logger.error("Unipile create_post error: %s", e)
                return None

    async def register_webhook(self, callback_url: str, events: list[str]) -> bool:
        """Register a webhook receiver with Unipile for real-time events."""
        url = f"{self.dsn}/api/v1/webhooks"
        payload = {
            "url": callback_url,
            "events": events,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                return res.status_code in (200, 201)
            except Exception as e:
                logger.error("Unipile register_webhook error: %s", e)
                return False
