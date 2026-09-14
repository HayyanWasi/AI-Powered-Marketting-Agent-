from pydantic import BaseModel, Field


class BrandSnapshot(BaseModel):
    brand_name: str = ""
    industry: str = ""
    tone_of_voice: str = ""
    personality_descriptors: list[str] = Field(default_factory=list)
    color_palette: list[str] = Field(default_factory=list)
    style_guidance: str = ""


class ImageGenerationState(BaseModel):
    base_idea: str
    brand_snapshot: BrandSnapshot
    brand_visual_translation: str = ""
    brand_adjustments: str = ""
    refinements: list[str] = Field(default_factory=list)
    current_final_prompt: str = ""
    iteration_count: int = 0
