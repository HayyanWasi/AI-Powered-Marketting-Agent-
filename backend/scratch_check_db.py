import asyncio

from src.services.supabase import SupabaseService


async def main():
    service = SupabaseService()
    try:
        # Check campaigns
        res = (
            service.client.table("campaigns")
            .select("id, name, metadata")
            .order("created_at", desc=True)
            .limit(3)
            .execute()
        )
        print("Recent Campaigns:")
        for row in res.data:
            print(f"- {row['name']} (ID: {row['id']})")
            print(f"  Metadata: {row['metadata']}")

        # Check guest profiles
        guest_res = (
            service.client.table("guest_profiles")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        print("\nLatest Guest Profile:")
        print(guest_res.data)

        # Check execution history
        hist_res = (
            service.client.table("execution_history")
            .select("*")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        print("\nRecent Execution History:")
        for row in hist_res.data:
            print(f"Step: {row.get('step_name')} Status: {row.get('status')}")

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    asyncio.run(main())
