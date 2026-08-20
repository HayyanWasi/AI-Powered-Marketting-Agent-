"""Live smoke test: real ContextBuilder -> Orchestrator run.

Usage:  uv run python scripts/smoke_pipeline.py [company_profile_id]

Hits real services (Supabase, DuckDuckGo, OpenAI/Gemini, Pollinations).
Not part of the pytest suite — run manually with real keys in .env.
"""

import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from src.agents.context_builder import ContextBuilder  # noqa: E402
from src.agents.orchestrator import Orchestrator  # noqa: E402
from src.services.supabase import SupabaseService  # noqa: E402


def pick_profile_id() -> str | None:
    """Use the first company profile in the DB if none was given."""
    try:
        service = SupabaseService()
        rows = (
            service.client.table("company_profiles").select("id, company_name").limit(5).execute()
        )
        if rows.data:
            print("Available profiles:")
            for row in rows.data:
                print(f"  {row['id']}  {row.get('company_name', '')}")
            return rows.data[0]["id"]
    except Exception as e:  # noqa: BLE001
        print(f"Could not list profiles: {e}")
    return None


async def main() -> None:
    profile_id = sys.argv[1] if len(sys.argv) > 1 else pick_profile_id()
    print(f"\nUsing company_profile_id: {profile_id}\n")

    builder = ContextBuilder()
    context = builder.build(
        company_profile_id=profile_id,
        guest_names=["Sam Altman"],
        event_name="AI Innovators Summit 2026",
        event_date="2026-08-15",
        venue="Expo Center Karachi",
        platforms=["linkedin", "instagram"],
        registration_link="https://example.com/register",
    )

    print(f"Brand: {context.brand.company_name!r}")
    print(f"Reference images: {len(context.brand.reference_image_urls)}")
    print(f"Guests: {[g.full_name for g in context.guests]}")

    result = await Orchestrator().execute(context)

    print(f"\nWorkflow success: {result.success} — {result.message}")
    for draft in result.context.content_drafts[:2]:
        print(f"\n--- Slot {draft.slot_id} ---")
        print(f"A: {draft.variant_a[:200]}")
        print(f"B: {draft.variant_b[:200]}")
        print(f"C: {draft.variant_c[:200]}")
        print(f"Image prompt: {draft.image_prompt[:200]}")
        print(f"Image URL:    {draft.image_url}")
        print(f"Image model:  {draft.image_model}")


if __name__ == "__main__":
    asyncio.run(main())
