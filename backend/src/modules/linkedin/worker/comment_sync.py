import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from src.config.supabase import get_supabase_client
from src.gateways.unipile_gateway import get_unipile_gateway

logger = logging.getLogger(__name__)


class CommentSyncWorker:
    def __init__(self):
        self.gateway = get_unipile_gateway()
        self.supabase = get_supabase_client()

    async def sync_all_accounts(self) -> None:
        """Poll comments for all connected accounts."""
        try:
            res = (
                self.supabase.table("linkedin_accounts")
                .select("*")
                .eq("status", "connected")
                .execute()
            )
            accounts = res.data or []
            for acc in accounts:
                try:
                    await self.sync_account(acc)
                except Exception as e:
                    logger.error("Failed to sync comments for account %s: %s", acc.get("id"), e)
        except Exception as e:
            logger.error("Comment sync job failed: %s", e)

    async def sync_account(self, account: dict[str, Any]) -> None:
        account_id = account["id"]
        unipile_account_id = account["unipile_account_id"]
        user_id = account["user_id"]

        unipile_acc = await self.gateway.get_account(unipile_account_id)
        if not unipile_acc:
            return

        own_provider_id = None
        conn_params = unipile_acc.get("connection_params", {})
        if "im" in conn_params:
            own_provider_id = conn_params["im"].get("id")

        res = (
            self.supabase.table("linkedin_posts")
            .select("id, unipile_post_id")
            .eq("linkedin_account_id", account_id)
            .not_.is_("unipile_post_id", "null")
            .execute()
        )
        posts = res.data or []

        for p in posts:
            social_id = p["unipile_post_id"]
            if not social_id:
                continue

            try:
                await self.sync_post_comments(
                    user_id, account_id, unipile_account_id, own_provider_id, social_id
                )
            except Exception as e:
                logger.error("Failed to sync comments for post %s: %s", social_id, e)

    async def sync_post_comments(
        self,
        user_id: str,
        account_id: str,
        unipile_account_id: str,
        own_provider_id: str,
        social_id: str,
    ) -> None:
        dsn = self.gateway.dsn.rstrip("/")
        url = f"{dsn}/api/v1/posts/{social_id}/comments"
        params = {"account_id": unipile_account_id, "limit": 100}
        headers = self.gateway._get_headers()

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url, headers=headers, params=params)
            if res.status_code != 200:
                logger.error("Unipile GET comments returned %s", res.status_code)
                return

            data = res.json()
            items = data.get("items", []) if isinstance(data, dict) else data

            for comment in items:
                remote_comment_id = comment.get("id")
                if not remote_comment_id:
                    continue

                await self._persist_comment(
                    user_id, account_id, social_id, own_provider_id, comment
                )

                # Check for replies
                reply_counter = comment.get("reply_counter")
                if reply_counter and isinstance(reply_counter, int) and reply_counter > 0:
                    reply_params = {
                        "account_id": unipile_account_id,
                        "limit": 100,
                        "comment_id": remote_comment_id,
                    }
                    reply_res = await client.get(url, headers=headers, params=reply_params)
                    if reply_res.status_code == 200:
                        reply_data = reply_res.json()
                        reply_items = (
                            reply_data.get("items", [])
                            if isinstance(reply_data, dict)
                            else reply_data
                        )
                        for reply in reply_items:
                            if reply.get("id"):
                                await self._persist_comment(
                                    user_id,
                                    account_id,
                                    social_id,
                                    own_provider_id,
                                    reply,
                                    parent_id=remote_comment_id,
                                )

    async def _persist_comment(
        self,
        user_id: str,
        account_id: str,
        social_id: str,
        own_provider_id: str,
        comment: dict,
        parent_id: str = None,
    ) -> None:
        remote_comment_id = comment.get("id")
        author_details = comment.get("author_details", {})
        author_id = author_details.get("id")

        author_str = comment.get("author")
        author_name = author_details.get("name") or (
            author_str if isinstance(author_str, str) else None
        )

        is_own = bool(own_provider_id and author_id == own_provider_id)
        text = comment.get("text", "")

        payload = {
            "user_id": user_id,
            "linkedin_account_id": account_id,
            "post_social_id": social_id,
            "remote_comment_id": remote_comment_id,
            "text": text,
            "author_provider_id": author_id,
            "author_name": author_name,
            "is_own_comment": is_own,
            "parent_comment_id": parent_id,
            "synced_at": datetime.now(UTC).isoformat(),
        }

        self.supabase.table("linkedin_comments").upsert(
            payload, on_conflict="linkedin_account_id, remote_comment_id"
        ).execute()


async def start_comment_sync_job():
    worker = CommentSyncWorker()
    await worker.sync_all_accounts()
