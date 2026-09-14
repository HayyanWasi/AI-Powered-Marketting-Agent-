import asyncio
import json
import logging

from pydantic import BaseModel, Field

from src.services.llm_service import LLMRequest, LLMService

logger = logging.getLogger(__name__)


class VideoScene(BaseModel):
    narration: str = Field(description="The exact words spoken in this scene (2-4 seconds long).")
    image_prompt: str = Field(description="Comma-separated Flux-optimized image generation prompt.")


class VideoScriptAgent:
    """Agent responsible for writing video scripts and visual prompts."""

    def __init__(self):
        self.llm = LLMService()
        self.system_prompt = """You are an award-winning cinematic Commercial Director and Storyteller.
Your mission is to craft a fast-paced, high-impact storytelling video script tailored EXACTLY to the user's campaign prompt.

### STRICT DURATION LIMIT (CRITICAL):
- TOTAL VIDEO MUST BE STRICTLY UNDER 25 SECONDS (Target: 14 to 18 seconds total).
- Generate EXACTLY 5 scenes.
- Each scene must be SHORT and PUNCHY: STRICTLY 5 to 8 words per sentence (approx. 2.5 to 3.0 seconds spoken per scene).
- Total word count across ALL 5 scenes combined must NOT exceed 40 words!
- DO NOT spell out raw URLs (like "http://..."). In spoken narration, say "Register at link below!" or "Link in bio to register!".

### CRITICAL RULES:
1. STRICT FACTUAL ACCURACY & NO HALLUCINATIONS:
   - If the user provides specific names, dates, or venues in their prompt, include them accurately.
   - NEVER invent or hallucinate specific names of people, guest speakers, organizations, or physical venues unless explicitly provided by the user in the prompt.
   - If no speaker or guest is mentioned, focus purely on the topic, attendee benefits, technology, and energy of the event.

2. 5-ACT STORYTELLING NARRATIVE ARC (EXACTLY 5 SCENES):
   - Scene 1 [The Hook]: Captivating opening question or bold statement introducing the subject. (5-8 words)
   - Scene 2 [The Challenge / Core Need]: Highlighting the transformation, challenge, or breakthrough. (5-8 words)
   - Scene 3 [The Experience / Highlight]: The core session, demonstration, or main highlight of the campaign. (5-8 words)
   - Scene 4 [Hands-On / Impact]: People interacting, learning, or experiencing the benefits. (5-8 words)
   - Scene 5 [Call to Action]: Clear, exciting call to action (register, visit, or join today). (5-8 words)

3. FLUX IMAGE PROMPTS (HYPER-REALISTIC & DYNAMIC):
   For each scene, write an ultra-detailed Flux image prompt matching that exact story beat:
   - Subject & Action: Real, expressive human characters engaged in the action.
   - Setting & Background: Photorealistic real-world setting matching the topic (modern auditorium, high-tech lab, cozy cafe, vibrant workshop, etc.).
   - Lighting & Camera: Cinematic rim lighting, 35mm lens, depth of field, 8k resolution, photorealistic.
   - Diverse Angles: Scene 1 wide cinematic, Scene 2 over-the-shoulder, Scene 3 medium portrait/stage, Scene 4 close-up collaborative hands-on, Scene 5 dynamic celebration or wide closing view.
   - Format: Comma-separated descriptive phrases, no punctuation marks other than commas.

### OUTPUT JSON FORMAT:
Output ONLY a valid JSON array of exactly 5 scene objects:
[
  {
    "narration": "What if autonomous agents could build the future?",
    "image_prompt": "Cinematic eye-level shot of ambitious engineers at a futuristic tech hub, glowing screens, soft ambient neon lighting, photorealistic, 8k, shot on 35mm lens"
  }
]"""

    async def generate_script(self, campaign_context: str) -> list[VideoScene]:
        """Generates a video script given a campaign context."""
        logger.info(
            "VideoScriptAgent: Generating video script for context: %s...", campaign_context[:50]
        )

        user_prompt = f"""Campaign Brief from User:
----------------------------------------
{campaign_context}
----------------------------------------

TASK:
Craft a 5-scene storytelling commercial script based strictly on the brief above.
Explicitly include all specific names, locations, topics, and event details mentioned by the user.
Generate the JSON array of scenes now."""

        request = LLMRequest(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            json_mode=True,
        )

        response = await asyncio.to_thread(self.llm.generate, request)

        try:
            # LLMService returns a string that should be JSON
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)
            scenes = [VideoScene(**item) for item in data]
            return scenes
        except Exception as e:
            logger.error(
                "Failed to parse VideoScriptAgent response: %s\nRaw response: %s", e, response.text
            )
            raise ValueError(
                f"Failed to generate valid video script. Error: {e}\nRaw Response: {response.text}"
            ) from e
