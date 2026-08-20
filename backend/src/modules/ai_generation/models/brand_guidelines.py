"""Brand guidelines model for AI Generation Engine."""

from dataclasses import dataclass
from typing import Any


@dataclass
class LogoSpecs:
    """Logo specifications for brand guidelines."""

    width: int
    height: int
    format: str
    background: str
    clear_space: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "background": self.background,
            "clear_space": self.clear_space,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogoSpecs":
        """Deserialize from dictionary."""
        return cls(
            width=data["width"],
            height=data["height"],
            format=data["format"],
            background=data["background"],
            clear_space=data["clear_space"],
        )


@dataclass
class BrandGuidelines:
    """Brand voice and style guidelines."""

    voice_tone: str
    color_palette: list[str]
    fonts: list[str]
    logo_specs: LogoSpecs
    brand_values: list[str]
    do_not_do: list[str]
    emoticons: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "voice_tone": self.voice_tone,
            "color_palette": self.color_palette,
            "fonts": self.fonts,
            "logo_specs": self.logo_specs.to_dict(),
            "brand_values": self.brand_values,
            "do_not_do": self.do_not_do,
            "emoticons": self.emoticons,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrandGuidelines":
        """Deserialize from dictionary."""
        return cls(
            voice_tone=data["voice_tone"],
            color_palette=data["color_palette"],
            fonts=data["fonts"],
            logo_specs=LogoSpecs.from_dict(data["logo_specs"]),
            brand_values=data["brand_values"],
            do_not_do=data["do_not_do"],
            emoticons=data["emoticons"],
        )
