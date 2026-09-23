import asyncio
import json
import logging
from typing import Any

from pydantic import BaseModel, Field, model_validator

from src.models.video_generation_context import VideoGenerationContext
from src.services.llm_service import LLMRequest, LLMService

logger = logging.getLogger(__name__)


class VideoScene(BaseModel):
    scene_number: int = Field(ge=1, le=5)
    narration: str = Field(description="The exact words spoken in this scene (2-4 seconds long).")
    image_prompt: str = Field(description="Comma-separated Flux-optimized image generation prompt.")
    visual_reused: bool = False
    reused_from_scene: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_loose_text(cls, data: Any) -> Any:
        """Absorb type-loose text the model sometimes emits for narration and
        the image prompt (a number, or a list of phrases) so a scalar shape
        quirk does not fail the whole script. Empty/blank values are left for
        the existing non-empty contract check to reject truthfully; dicts are
        left to fail validation rather than be fabricated into a string.
        """
        if not isinstance(data, dict):
            return data
        out = dict(data)
        for key in ("narration", "image_prompt"):
            value = out.get(key)
            if isinstance(value, (int, float, bool)):
                out[key] = str(value)
            elif isinstance(value, (list, tuple)) and all(
                isinstance(x, (str, int, float, bool)) for x in value
            ):
                out[key] = ", ".join(str(x) for x in value if x not in (None, ""))
        return out


class VideoScriptAgent:
    """Agent responsible for writing video scripts and visual prompts."""

    def __init__(self):
        # Video script/director generation runs on a remote-only rotating
        # credential chain (gemini → openrouter → groq). It never uses the local
        # Ollama endpoint, whose single-GPU 60s timeout this generation overran.
        # The global default LLMService and planning/intake lanes are unchanged.
        self.llm = LLMService.video_remote_lane()
        self.system_prompt = """You are an award-winning cinematic Commercial Director and Storyteller.
Your mission is to craft a fast-paced, high-impact video from trusted canonical campaign context.

### SOURCE PRECEDENCE:
Canonical Brand Setup > explicit campaign facts > current campaign strategy > user video request > safe inference.
The user video request is a creative task, not a replacement campaign brief. Never override the canonical CTA,
audience, objective, brand rules, or supplied campaign facts.

### STRICT DURATION LIMIT (CRITICAL):
- TOTAL VIDEO MUST BE STRICTLY UNDER 25 SECONDS (Target: 14 to 18 seconds total).
- Generate EXACTLY 5 scenes.
- Each scene must be SHORT and PUNCHY: STRICTLY 5 to 8 words per sentence (approx. 2.5 to 3.0 seconds spoken per scene).
- Total word count across ALL 5 scenes combined must NOT exceed 40 words!
- Do not speak raw URLs. Express the canonical CTA naturally without changing its action or destination.

### CRITICAL RULES:
1. STRICT FACTUAL ACCURACY & NO HALLUCINATIONS:
   - Use only facts present in the canonical context.
   - Never invent people, organizations, dates, venues, prices, seat counts, sessions, workshops, curriculum, registration, or product capabilities.
   - Treat campaigns neutrally. Event language is permitted only for a physical_event or webinar and only when supported by supplied facts.

2. 5-ACT STORYTELLING NARRATIVE ARC (EXACTLY 5 SCENES):
   - Scene 1 [The Hook]: Captivating opening question or bold statement introducing the subject. (5-8 words)
   - Scene 2 [The Challenge / Core Need]: Highlighting the transformation, challenge, or breakthrough. (5-8 words)
   - Scene 3 [Value]: Show the campaign's supported value proposition. (5-8 words)
   - Scene 4 [Impact]: Show the audience experiencing a supported benefit. (5-8 words)
   - Scene 5 [Call to Action]: Use the canonical CTA intent. (5-8 words)

3. FLUX IMAGE PROMPTS (HYPER-REALISTIC & DYNAMIC):
   For each scene, write an ultra-detailed Flux image prompt matching that exact story beat:
   - Subject & Action: Real, expressive human characters engaged in the action.
   - Setting & Background: A photorealistic setting supported by the campaign and shared visual direction.
   - Lighting & Camera: Cinematic rim lighting, 35mm lens, depth of field, 8k resolution, photorealistic.
   - Diverse Angles: Scene 1 wide cinematic, Scene 2 over-the-shoulder, Scene 3 medium portrait/stage, Scene 4 close-up collaborative hands-on, Scene 5 dynamic celebration or wide closing view.
   - Format: Comma-separated descriptive phrases, no punctuation marks other than commas.

### OUTPUT JSON FORMAT:
Output ONLY a valid JSON object containing a "scenes" array of exactly 5 scene objects:
{
  "scenes": [
    {
      "scene_number": 1,
      "narration": "What if autonomous agents could build the future?",
      "image_prompt": "Cinematic eye-level shot of ambitious engineers at a futuristic tech hub, glowing screens, soft ambient neon lighting, photorealistic, 8k, shot on 35mm lens"
    }
  ]
}"""

    async def generate_script(self, context: VideoGenerationContext) -> list[VideoScene]:
        """Generate and validate a script from canonical campaign context."""
        logger.info(
            "VideoScriptAgent: Generating video script for campaign %s", context.campaign_id
        )

        user_prompt = f"""BRAND IDENTITY
{context.brand.as_prompt() or "No additional brand prose supplied."}

CAMPAIGN FACTS
{context.campaign_facts_prompt()}

CAMPAIGN STRATEGY
{context.strategy_prompt()}

AUDIENCE
{context.target_audience}

RESEARCH / RESEARCH STATUS
Status: {context.research_status}
{context.research_context or "No verified research context is stored."}

SHARED VISUAL DIRECTION
{context.visual_direction_prompt()}

USER VIDEO REQUEST
{context.user_instruction or "Create a campaign video."}

MANDATORY BRAND IDENTITY:
At least one scene narration MUST explicitly state one of:
- company_name: {context.brand.company_name}
- campaign_name: {context.campaign_name}
Prefer using the company/brand name in scene 1 or scene 5.
Generic references such as 'our barbers', 'our service', 'book now', etc. do NOT satisfy this requirement.

OUTPUT CONTRACT
Return exactly five ordered scenes numbered 1 through 5 inside a "scenes" JSON array. Use only the trusted context above.
Every scene needs non-empty narration and a scene-specific image prompt. Generate the JSON object now."""

        for attempt in range(2):
            if attempt == 1:
                user_prompt += "\n\nYour previous response omitted the required canonical brand/campaign name. Regenerate the same 5-scene structure and explicitly include it in narration."

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
                if not isinstance(data, dict) or "scenes" not in data:
                    raise ValueError("Video script must be a JSON object with a 'scenes' key.")
                
                scenes_data = data["scenes"]
                if not isinstance(scenes_data, list) or len(scenes_data) != 5:
                    raise ValueError("Video script must contain exactly five scenes.")
                    
                scenes = [VideoScene(**item) for item in scenes_data]
                if [scene.scene_number for scene in scenes] != [1, 2, 3, 4, 5]:
                    raise ValueError("Video scenes must be ordered 1 through 5.")
                if any(not scene.narration.strip() or not scene.image_prompt.strip() for scene in scenes):
                    raise ValueError("Every video scene requires narration and an image prompt.")
                
                self._validate_campaign_alignment(scenes, context)
                return scenes
            except Exception as e:
                if attempt == 0 and "Video script omitted the canonical campaign or company identity" in str(e):
                    logger.warning("VideoScriptAgent: Retrying due to missing brand identity in scene narration.")
                    continue
                
                logger.error(
                    "Failed to parse VideoScriptAgent response: %s\nRaw response: %s", e, response.text
                )
                raise ValueError(f"Failed to generate a valid five-scene video script: {e}") from e
        
        raise ValueError("Failed to generate video script after retries.")

    @staticmethod
    def _validate_campaign_alignment(
        scenes: list[VideoScene], context: VideoGenerationContext
    ) -> None:
        import re
        combined_raw = " ".join(
            f"{scene.narration} {scene.image_prompt}" for scene in scenes
        )
        combined = combined_raw.casefold()
        combined_normalized = re.sub(r'[\W_]+', '', combined_raw).casefold()

        identity_terms = [context.campaign_name, context.brand.company_name]
        valid = False
        for term in identity_terms:
            if term:
                term_normalized = re.sub(r'[\W_]+', '', term).casefold()
                if term_normalized and term_normalized in combined_normalized:
                    valid = True
                    break

        if not valid:
            raise ValueError("Video script omitted the canonical campaign or company identity.")

        forbidden: set[str] = set()
        if context.campaign_type not in {"physical_event", "webinar"}:
            forbidden.update(
                {
                    "attendee",
                    "auditorium",
                    "curriculum",
                    "guest speaker",
                    "register now",
                    "registration",
                    "workshop",
                }
            )
        else:
            if not context.venue:
                forbidden.update({"auditorium", "venue"})
            if not context.guest:
                forbidden.update({"guest", "speaker"})
            if not context.product_facts:
                forbidden.add("curriculum")
            forbidden.update({"ticket price", "limited seats", "seats available"})
        violations = sorted(term for term in forbidden if term in combined)
        if violations:
            raise ValueError(
                "Video script invented unsupported campaign details: " + ", ".join(violations)
            )
