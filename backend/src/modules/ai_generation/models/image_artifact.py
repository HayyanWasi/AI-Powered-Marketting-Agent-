"""Image artifact model for AI Generation Engine."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ImageMetadata:
    """Technical metadata for generated images."""

    width: int
    height: int
    format: str
    size_bytes: int
    aspects_ratio: float
    file_path: Optional[str] = None
    cloud_storage_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metadata to dictionary."""
        return {
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "aspects_ratio": self.aspects_ratio,
            "file_path": self.file_path,
            "cloud_storage_path": self.cloud_storage_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageMetadata":
        """Deserialize metadata from dictionary."""
        return cls(
            width=data["width"],
            height=data["height"],
            format=data["format"],
            size_bytes=data["size_bytes"],
            aspects_ratio=data["aspects_ratio"],
            file_path=data.get("file_path"),
            cloud_storage_path=data.get("cloud_storage_path"),
        )


@dataclass
class BrandAlignmentScore:
    """Brand compliance measurement for generated images."""

    overall_score: float
    elements_checked: List[str]
    scores: Dict[str, float]
    issues: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize score to dictionary."""
        return {
            "overall_score": self.overall_score,
            "elements_checked": self.elements_checked,
            "scores": self.scores,
            "issues": self.issues,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrandAlignmentScore":
        """Deserialize score from dictionary."""
        return cls(
            overall_score=data["overall_score"],
            elements_checked=data["elements_checked"],
            scores=data["scores"],
            issues=data["issues"],
        )


@dataclass
class PlatformSuitabilityScore:
    """Platform compatibility measurement for generated images."""

    overall_score: float
    criteria: List[str]
    scores: Dict[str, float]
    requirements_met: List[str]
    requirements_failed: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize score to dictionary."""
        return {
            "overall_score": self.overall_score,
            "criteria": self.criteria,
            "scores": self.scores,
            "requirements_met": self.requirements_met,
            "requirements_failed": self.requirements_failed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlatformSuitabilityScore":
        """Deserialize score from dictionary."""
        return cls(
            overall_score=data["overall_score"],
            criteria=data["criteria"],
            scores=data["scores"],
            requirements_met=data["requirements_met"],
            requirements_failed=data["requirements_failed"],
        )


@dataclass
class StyleGuidelines:
    """Artistic style requirements for image generation."""

    artistic_style: str
    color_scheme: List[str]
    visual_mood: str
    typography: str
    composition: str
    lighting: str
    filters: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize guidelines to dictionary."""
        return {
            "artistic_style": self.artistic_style,
            "color_scheme": self.color_scheme,
            "visual_mood": self.visual_mood,
            "typography": self.typography,
            "composition": self.composition,
            "lighting": self.lighting,
            "filters": self.filters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StyleGuidelines":
        """Deserialize guidelines from dictionary."""
        return cls(
            artistic_style=data["artistic_style"],
            color_scheme=data["color_scheme"],
            visual_mood=data["visual_mood"],
            typography=data["typography"],
            composition=data["composition"],
            lighting=data["lighting"],
            filters=data["filters"],
        )


@dataclass
class BrandElement:
    """Brand components to include in image."""

    element_type: str
    location: str
    opacity: float
    size_spec: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize element to dictionary."""
        return {
            "element_type": self.element_type,
            "location": self.location,
            "opacity": self.opacity,
            "size_spec": self.size_spec,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrandElement":
        """Deserialize element from dictionary."""
        return cls(
            element_type=data["element_type"],
            location=data["location"],
            opacity=data["opacity"],
            size_spec=data["size_spec"],
        )


@dataclass
class VisualElement:
    """Visual concepts for image generation."""

    concept: str
    description: str
    priority: int
    inclusion_requirement: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialize element to dictionary."""
        return {
            "concept": self.concept,
            "description": self.description,
            "priority": self.priority,
            "inclusion_requirement": self.inclusion_requirement,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisualElement":
        """Deserialize element from dictionary."""
        return cls(
            concept=data["concept"],
            description=data["description"],
            priority=data["priority"],
            inclusion_requirement=data["inclusion_requirement"],
        )


@dataclass
class CompositionGuidelines:
    """Layout and composition rules for image generation."""

    layout_type: str
    focal_points: List[str]
    depth_of_field: str
    perspective: str
    negative_space: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize guidelines to dictionary."""
        return {
            "layout_type": self.layout_type,
            "focal_points": self.focal_points,
            "depth_of_field": self.depth_of_field,
            "perspective": self.perspective,
            "negative_space": self.negative_space,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompositionGuidelines":
        """Deserialize guidelines from dictionary."""
        return cls(
            layout_type=data["layout_type"],
            focal_points=data["focal_points"],
            depth_of_field=data["depth_of_field"],
            perspective=data["perspective"],
            negative_space=data["negative_space"],
        )


@dataclass
class ValidationError:
    """Individual validation error."""

    code: str
    message: str
    severity: str
    field: Optional[str] = None
    suggested_fix: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize error to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "field": self.field,
            "suggested_fix": self.suggested_fix,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationError":
        """Deserialize error from dictionary."""
        return cls(
            code=data["code"],
            message=data["message"],
            severity=data["severity"],
            field=data.get("field"),
            suggested_fix=data.get("suggested_fix"),
        )


@dataclass
class ValidationWarning:
    """Individual validation warning."""

    code: str
    message: str
    field: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize warning to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationWarning":
        """Deserialize warning from dictionary."""
        return cls(
            code=data["code"],
            message=data["message"],
            field=data.get("field"),
        )


@dataclass
class ContentBlock:
    """Structured content element."""

    type: str
    content: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize block to dictionary."""
        return {
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentBlock":
        """Deserialize block from dictionary."""
        return cls(
            type=data["type"],
            content=data["content"],
            metadata=data["metadata"],
        )


@dataclass
class ValidationResults:
    """Validation outcome tracking."""

    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]
    compliance_scores: Dict[str, float]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize results to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "compliance_scores": self.compliance_scores,
            "recommendations": self.recommendations,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationResults":
        """Deserialize results from dictionary."""
        return cls(
            is_valid=data["is_valid"],
            errors=[ValidationError.from_dict(e) for e in data["errors"]],
            warnings=[ValidationWarning.from_dict(w) for w in data["warnings"]],
            compliance_scores=data["compliance_scores"],
            recommendations=data["recommendations"],
        )


@dataclass
class ImageArtifact:
    """
    Generated campaign image created from the Image Prompt Artifact.
    The final visual asset with comprehensive metadata and scoring.
    """

    id: str
    generated_at: datetime
    prompt_id: str
    platform: str
    image_url: str
    thumbnail_url: str
    metadata: ImageMetadata
    brand_alignment: BrandAlignmentScore
    platform_suitability: PlatformSuitabilityScore
    validation_results: Optional[ValidationResults] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize image to dictionary for storage/transmission."""
        return {
            "id": self.id,
            "generated_at": self.generated_at.isoformat(),
            "prompt_id": self.prompt_id,
            "platform": self.platform,
            "image_url": self.image_url,
            "thumbnail_url": self.thumbnail_url,
            "metadata": self.metadata.to_dict(),
            "brand_alignment": self.brand_alignment.to_dict(),
            "platform_suitability": self.platform_suitability.to_dict(),
            "validation_results": (
                self.validation_results.to_dict() if self.validation_results else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageArtifact":
        """Deserialize image from dictionary."""
        return cls(
            id=data["id"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            prompt_id=data["prompt_id"],
            platform=data["platform"],
            image_url=data["image_url"],
            thumbnail_url=data["thumbnail_url"],
            metadata=ImageMetadata.from_dict(data["metadata"]),
            brand_alignment=BrandAlignmentScore.from_dict(data["brand_alignment"]),
            platform_suitability=PlatformSuitabilityScore.from_dict(data["platform_suitability"]),
            validation_results=(
                ValidationResults.from_dict(data.get("validation_results"))
                if data.get("validation_results")
                else None
            ),
        )
