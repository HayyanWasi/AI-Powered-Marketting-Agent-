import asyncio
from uuid import uuid4

from src.models.intake import IntakeChecklist
from src.services.intake_chat_service import IntakeChatService


async def run_simulation():
    service = IntakeChatService()
    cid = uuid4()
    history = []
    current_checklist = IntakeChecklist()

    turns = [
        "i want to host an agentic ai seminar",
        "target audience industry professionals honge and intermediate level students",
        "20 august 2026 at bahria auditorium karachi",
        "guest speaker Zia Ullah Khan hain agentic ai architect",
        "curriculum will be loop engineering and spec driven development",
        "outcome will be building production ready autonomous agents",
        "free of cost event hai",
        "https://forms.gle/agentic-ai-seminar-register"
    ]

    print("=== STARTING MULTI-TURN INTAKE SIMULATION ===", flush=True)
    print(f"Campaign ID: {cid}\n", flush=True)

    for i, user_msg in enumerate(turns, 1):
        print(f"Turn {i} USER: \"{user_msg}\"", flush=True)
        res = await service.process_chat_turn(
            campaign_id=cid,
            user_message=user_msg,
            history=history,
            current_checklist=current_checklist,
        )

        reply = res["reply"]
        current_checklist = res["checklist"]
        is_complete = res["is_complete"]

        print(f"Turn {i} AI REPLY: \"{reply}\"", flush=True)
        print(f"Turn {i} COLLECTED STATE: {current_checklist.model_dump(exclude_none=True)}", flush=True)
        print(f"Turn {i} IS COMPLETE: {is_complete}", flush=True)
        print("-" * 60, flush=True)


        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": reply})

if __name__ == "__main__":
    asyncio.run(run_simulation())
