"""Mock Unipile Gateway — Returns dummy JSON data for development.

Activated when ``USE_MOCK_UNIPILE=true`` in ``.env``.  Zero network calls.
Every method logs with a ``[MOCK]`` prefix for visibility.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.gateways.unipile_gateway import UnipileGateway

logger = logging.getLogger(__name__)


class MockUnipileGateway(UnipileGateway):
    """Drop-in replacement for UnipileGateway that returns realistic dummy data.

    Inherits from UnipileGateway so it passes isinstance() checks.
    All methods are overridden to avoid any real HTTP calls.
    """

    def __init__(self, **kwargs: Any) -> None:
        # Skip parent __init__ — we don't need DSN/token for mocks
        self.dsn = "https://mock.unipile.local"
        self.token = "mock_token"
        self.timeout = 15.0
        logger.warning("[MOCK] MockUnipileGateway initialized — no real API calls")

    async def list_accounts(self) -> list[dict[str, Any]]:
        logger.info("[MOCK] list_accounts")
        return [
            {
                "id": "mock_account_001",
                "provider": "LINKEDIN",
                "status": "connected",
                "name": "Mock LinkedIn Account",
            }
        ]

    async def get_account(self, account_id: str) -> dict[str, Any] | None:
        logger.info("[MOCK] get_account(%s)", account_id)
        return {
            "id": account_id,
            "provider": "LINKEDIN",
            "status": "connected",
            "name": "Mock LinkedIn Account",
        }

    async def visit_profile(self, account_id: str, linkedin_id: str) -> bool:
        logger.info("[MOCK] visit_profile(%s, %s)", account_id, linkedin_id)
        return True

    async def send_connection_request(
        self, account_id: str, linkedin_id: str, message: str
    ) -> str | None:
        invite_id = f"mock_invite_{uuid4().hex[:8]}"
        logger.info(
            "[MOCK] send_connection_request(%s, %s) -> %s",
            account_id,
            linkedin_id,
            invite_id,
        )
        return invite_id

    async def withdraw_invitation(self, account_id: str, invite_id: str) -> bool:
        logger.info("[MOCK] withdraw_invitation(%s, %s)", account_id, invite_id)
        return True

    async def send_message(self, account_id: str, chat_id: str, text: str) -> str | None:
        msg_id = f"mock_msg_{uuid4().hex[:8]}"
        logger.info("[MOCK] send_message(%s, %s) -> %s", account_id, chat_id, msg_id)
        return msg_id

    async def create_post(self, account_id: str, text: str) -> str | None:
        post_id = f"mock_post_{uuid4().hex[:8]}"
        logger.info("[MOCK] create_post(%s) -> %s", account_id, post_id)
        return post_id

    async def register_webhook(self, callback_url: str, events: list[str]) -> bool:
        logger.info("[MOCK] register_webhook(%s, %s)", callback_url, events)
        return True

    # ── New methods for scheduler engine ──────────────────────────────────

    async def search_people(
        self, account_id: str, keywords: str, limit: int = 150
    ) -> list[dict[str, Any]]:
        logger.info("[MOCK] search_people(%s, keywords=%s, limit=%d)", account_id, keywords, limit)
        return [
            {
                "provider_id": f"mock_profile_{i}",
                "name": f"Mock User {i}",
                "headline": f"Mock {keywords} Professional",
            }
            for i in range(min(limit, 20))
        ]

    async def get_user_posts(
        self, account_id: str, profile_id: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        logger.info("[MOCK] get_user_posts(%s, %s, limit=%d)", account_id, profile_id, limit)
        return [
            {
                "id": f"mock_post_{profile_id}_{i}",
                "text": (
                    f"This is a mock post about industry trends and technical "
                    f"challenges in building scalable systems. Post #{i} from "
                    f"profile {profile_id}. The key insight is that most teams "
                    f"underestimate the data migration complexity."
                ),
                "created_at": datetime.now(UTC).isoformat(),
                "author": {"id": profile_id, "name": f"Mock Author {profile_id}"},
            }
            for i in range(limit)
        ]

    async def like_post(self, account_id: str, post_id: str) -> bool:
        logger.info("[MOCK] like_post(%s, %s)", account_id, post_id)
        return True

    async def comment_on_post(self, account_id: str, post_id: str, text: str) -> str | None:
        comment_id = f"mock_comment_{uuid4().hex[:8]}"
        logger.info(
            "[MOCK] comment_on_post(%s, %s): %s -> %s",
            account_id,
            post_id,
            text[:60],
            comment_id,
        )
        return comment_id

    async def get_feed_posts(self, account_id: str, limit: int = 10) -> list[dict[str, Any]]:
        logger.info("[MOCK] get_feed_posts(%s, limit=%d)", account_id, limit)
        return [
            {
                "id": f"mock_feed_post_{i}",
                "text": f"Mock feed post #{i} about engineering leadership.",
                "created_at": datetime.now(UTC).isoformat(),
            }
            for i in range(limit)
        ]

    async def check_relation(self, account_id: str, linkedin_id: str) -> bool:
        logger.info("[MOCK] check_relation(%s, %s)", account_id, linkedin_id)
        return True
