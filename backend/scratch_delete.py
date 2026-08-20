import asyncio
import logging

from src.repositories.base import BaseRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def delete_campaigns():
    logger.info("Cleaning up old test campaigns...")
    tables = [
        "campaign_assets",
        "campaign_history",
        "campaign_configurations",
        "intake_messages",
        "intake_checklists",
        "campaigns",
    ]
    for tbl in tables:
        try:
            repo = BaseRepository(tbl)
            res = repo.client.table(tbl).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            logger.info("Cleared table '%s': %s records deleted", tbl, len(res.data) if res.data else 0)
        except Exception as e:
            logger.warning("Could not clear table '%s': %s", tbl, e)

if __name__ == "__main__":
    asyncio.run(delete_campaigns())
