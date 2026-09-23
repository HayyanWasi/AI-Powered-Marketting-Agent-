import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from src.config.supabase import get_supabase_client
from src.gateways.unipile_gateway import get_unipile_gateway

logger = logging.getLogger(__name__)


class ReplyService:
    def __init__(self):
        self.gateway = get_unipile_gateway()
        self.supabase = get_supabase_client()

    async def send_manual_reply(
        self, user_id: str, local_comment_id: str, reply_text: str
    ) -> dict[str, Any]:
        """Send a manual reply to an inbound comment."""

        # 1. Fetch local comment and verify ownership
        res = (
            self.supabase.table("linkedin_comments")
            .select("*")
            .eq("id", local_comment_id)
            .eq("user_id", user_id)
            .execute()
        )
        comments = res.data or []
        if not comments:
            raise ValueError("Target comment not found or not owned by user.")

        target_comment = comments[0]
        account_id = target_comment["linkedin_account_id"]
        post_social_id = target_comment["post_social_id"]
        remote_comment_id = target_comment["remote_comment_id"]

        # 2. Get Unipile account ID
        acc_res = (
            self.supabase.table("linkedin_accounts")
            .select("unipile_account_id")
            .eq("id", account_id)
            .execute()
        )
        if not acc_res.data:
            raise ValueError("LinkedIn account not found.")
        unipile_account_id = acc_res.data[0]["unipile_account_id"]

        # 3. Create local reply record idempotently
        payload = {
            "user_id": user_id,
            "linkedin_account_id": account_id,
            "target_remote_comment_id": remote_comment_id,
            "reply_text": reply_text,
            "status": "PENDING",
        }

        reply_res = self.supabase.table("linkedin_replies").insert(payload).execute()
        if not reply_res.data:
            raise ValueError("Could not claim reply locally. Duplicate?")

        reply_record_id = reply_res.data[0]["id"]

        # 4. Send to Unipile
        dsn = self.gateway.dsn.rstrip("/")
        url = f"{dsn}/api/v1/posts/{post_social_id}/comments"

        unipile_payload = {
            "account_id": unipile_account_id,
            "text": reply_text,
            "comment_id": remote_comment_id,  # Unipile payload for replying to a comment
        }
        headers = self.gateway._get_headers()

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, headers=headers, json=unipile_payload)
                if res.status_code in (200, 201):
                    data = res.json()
                    remote_reply_id = data.get("comment_id") or data.get("id")

                    self.supabase.table("linkedin_replies").update(
                        {
                            "status": "SENT",
                            "remote_reply_id": remote_reply_id,
                            "sent_at": datetime.now(UTC).isoformat(),
                        }
                    ).eq("id", reply_record_id).execute()

                    return {
                        "status": "success",
                        "reply_id": reply_record_id,
                        "remote_id": remote_reply_id,
                    }
                else:
                    self.supabase.table("linkedin_replies").update({"status": "FAILED"}).eq(
                        "id", reply_record_id
                    ).execute()
                    raise ValueError(f"Unipile error: {res.text}")
        except Exception as e:
            self.supabase.table("linkedin_replies").update({"status": "FAILED"}).eq(
                "id", reply_record_id
            ).execute()
            raise e
