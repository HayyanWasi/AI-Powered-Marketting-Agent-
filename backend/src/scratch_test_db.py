import asyncio
from uuid import uuid4

from src.models.intake import IntakeChecklist
from src.services.intake_chat_service import IntakeChatService


async def test():
    service = IntakeChatService()
    cid = uuid4()
    print("Testing save and get checklist for campaign:", cid)

    cl = IntakeChecklist(event_name="Test Seminar", target_audience="Students", category="seminar")
    service._save_checklist(cid, cl)

    retrieved = await service.get_checklist(cid)
    print("Retrieved checklist from DB:", retrieved.model_dump())


if __name__ == "__main__":
    asyncio.run(test())
