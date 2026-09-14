import asyncio

from src.services.supabase import SupabaseService


async def main():
    service = SupabaseService()
    try:
        campaign_id = "b975d055-6335-4a52-9753-ceaf0cca5c88"
        hist_res = (
            service.client.table("campaign_history")
            .select("*")
            .eq("campaign_id", campaign_id)
            .order("timestamp", desc=False)
            .execute()
        )
        print(f"\\nCampaign History for {campaign_id}:")
        for row in hist_res.data:
            details_str = str(row.get("details"))
            print(
                f"Time: {row.get('timestamp')} Action: {row.get('action')} Details: {details_str[:400]}"
            )

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    asyncio.run(main())
