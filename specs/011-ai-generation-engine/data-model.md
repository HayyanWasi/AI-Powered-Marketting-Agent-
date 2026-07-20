# AI Generation Engine Data Model

## Overview

Data models for the AI Generation Engine module define the complete specification of all possible inputs and outputs through the generation pipeline. These models support deterministic artifact transformation and immutable data contracts.

## Entities

### GenerationContext

**Purpose**: Complete campaign context assembled before generation begins. Serves as the single source of truth for all generation stages.

**Fields**:

```python
@dataclass
class GenerationContext:
    campaign_context: CampaignContext
    company_profile: CompanyProfile
    audience: Audience
    platforms: List[str]
    brand_guidelines: BrandGuidelines
    reference_materials: List[ReferenceMaterial]
    user_intent: Optional[UserIntent]
```

**Required Fields**:
- `campaign_context`: Campaign parameters including goals, target audience segments, budget, timeline
- `company_profile`: Company brand information, voice, values, positioning
- `audience`: Target audience demographics, interests, pain points, buying behavior
- `platforms`: List of target platforms (e.g., LinkedIn, Instagram, Twitter)
- `brand_guidelines`: Brand voice tone, style guidelines, logo specifications, color palette
- `reference_materials`: Relevant assets, benchmarks, competitor examples, previous campaigns

**Optional Fields**:
- `user_intent`: Additional instructions for specific content variations or emphasis

---

### StrategyArtifact

**Purpose**: Structured campaign strategy produced from the Generation Context. Defines the foundation for subsequent content generation.

**Fields**:

```python
@dataclass
class StrategyArtifact:
    id: str
    generated_at: datetime
    audience_strategy: AudienceStrategy
    messaging_strategy: MessagingStrategy
    platform_strategy: PlatformStrategy
    seo_strategy: SEOstrategy
    campaign_strategy: CampaignStrategy
    validation_results: Optional[ValidationResults]
```

**Required Fields**:
- `id`: Unique identifier for the strategy
- `generated_at`: Timestamp when strategy was created
- `audience_strategy`: Target audience targeting approach and messaging
- `messaging_strategy`: Core value propositions and key messages
- `platform_strategy`: Platform-specific adaptation requirements
- `seo_strategy`: Search optimization considerations
- `campaign_strategy`: Overall campaign goals and KPIs

**Optional Fields**:
- `validation_results`: Validation of strategy against business rules

---

### CopyArtifact

**Purpose**: Platform-specific marketing copy generated from the Strategy Artifact. Contains platform-adapted content.

**Fields**:

```python
@dataclass
class CopyArtifact:
    id: str
    generated_at: datetime
    strategy_id: str
    platform: str
    headlines: List[str]
    captions: List[str]
    ctas: List[str]
    hashtags: List[str]
    content_blocks: List[ContentBlock]
    validation_results: Optional[ValidationResults]
```

**Required Fields**:
- `id`: Unique identifier for the copy
- `generated_at`: Timestamp when copy was created
- `strategy_id`: Reference to source StrategyArtifact
- `platform`: Target platform identifier
- `headlines`: Ad copy headlines
- `captions`: Supporting body text
- `ctas`: Call-to-action phrases
- `hashtags`: Platform-specific hashtags

**Optional Fields**:
- `content_blocks`: Additional structured content elements
- `validation_results`: Validation results for copy compliance

---

### ImagePromptArtifact

**Purpose**: Structured image prompt derived from approved Copy and Strategy Artifacts. Ready for image generation.

**Fields**:

```python
@dataclass
class ImagePromptArtifact:
    id: str
    generated_at: datetime
    strategy_id: str
    copy_id: str
    platform: str
    prompt_text: str
    style_guidelines: StyleGuidelines
    brand_elements: List[BrandElement]
    visual_elements: List[VisualElement]
    composition_guidelines: CompositionGuidelines
    validation_results: Optional[ValidationResults]
```

**Required Fields**:
- `id`: Unique identifier for the image prompt
- `generated_at`: Timestamp when prompt was created
- `strategy_id`: Reference to source StrategyArtifact
- `copy_id`: Reference to source CopyArtifact
- `platform`: Target platform identifier
- `prompt_text`: Complete prompt for image generation
- `style_guidelines`: Artistic style requirements
- `brand_elements`: Brand elements to include (logo, colors, etc.)
- `visual_elements`: Visual concepts and imagery
- `composition_guidelines`: Layout and composition rules

**Optional Fields**:
- `validation_results`: Validation results for prompt compliance

---

### ImageArtifact

**Purpose**: Generated campaign image created from the Image Prompt Artifact. The final visual asset.

**Fields**:

```python
@dataclass
class ImageArtifact:
    id: str
    generated_at: datetime
    prompt_id: str
    platform: str
    image_url: str
    thumbnail_url: str
    metadata: ImageMetadata
    brand_alignment: BrandAlignmentScore
    platform_suitability: PlatformSuitabilityScore
    validation_results: Optional[ValidationResults]
```

**Required Fields**:
- `id`: Unique identifier for the generated image
- `generated_at`: Timestamp when image was created
- `prompt_id`: Reference to source ImagePromptArtifact
- `platform`: Target platform identifier
- `image_url`: URL to the generated image
- `thumbnail_url`: URL to thumbnail version
- `metadata`: Technical metadata (dimensions, format, size, etc.)
- `brand_alignment`: Score measuring brand guideline compliance
- `platform_suitability`: Score for platform-specific requirements

**Optional Fields**:
- `validation_results`: Validation results for image compliance

---

### ValidationArtifact

**Purpose**: Validation results describing compliance with business rules and platform requirements. Returned after each stage.

**Fields**:

```python
@dataclass
class ValidationArtifact:
    id: str
    generated_at: datetime
    artifact_type: ArtifactType
    artifact_id: str
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]
    compliance_scores: Dict[str, float]
    recommendations: List[str]
    validated_by: Optional[str]
```

**Required Fields**:
- `id`: Unique identifier for the validation
- `generated_at`: Timestamp when validation was performed
- `artifact_type`: Type of artifact being validated
- `artifact_id`: Reference to the artifact being validated
- `is_valid`: Overall validation result
- `errors`: List of validation errors found
- `warnings`: List of validation warnings
- `compliance_scores`: Scores for different compliance criteria

**Optional Fields**:
- `recommendations`: Suggested fixes for validation issues
- `validated_by`: System or component that performed validation

---

### Supporting Models

#### BrandGuidelines
**Style and brand identity rules**:
```python
@dataclass
class BrandGuidelines:
    voice_tone: str  # formal, casual, authoritative, conversational
    color_palette: List[str]
    fonts: List[str]
    logo_specs: LogoSpecs
    brand_values: List[str]
    do_not_do: List[str]
    emoticons: List[str]
```

#### ValidationResults
**Validation outcome tracking**:
```python
@dataclass
class ValidationResults:
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]
    compliance_scores: Dict[str, float]
    recommendations: List[str]
```

#### ValidationError
**Individual validation error**:
```python
@dataclass
class ValidationError:
    code: str
    message: str
    severity: str  # error, warning, info
    field: Optional[str]
    suggested_fix: Optional[str]
```

#### ContentBlock
**Structured content element**:
```python
@dataclass
class ContentBlock:
    type: str  # heading, paragraph, bullet, quote
    content: str
    metadata: Dict[str, Any]
```

#### ImageMetadata
**Technical image information**:
```python
@dataclass
class ImageMetadata:
    width: int
    height: int
    format: str
    size_bytes: int
    aspects_ratio: float
    file_path: Optional[str]
    cloud_storage_path: Optional[str]
```

#### StyleGuidelines
**Artistic style specifications**:
```python
@dataclass
class StyleGuidelines:
    artistic_style: str
    color_scheme: List[str]
    visual_mood: str
    typography: str
    composition: str
    lighting: str
    filters: List[str]
```

#### BrandElement
**Brand components to include**:
```python
@dataclass
class BrandElement:
    element_type: str  # logo, colors, tagline, product
    location: str  # top-left, center, background
    opacity: float
    size_spec: Dict[str, int]
```

#### VisualElement
**Visual concepts for image**:
```python
@dataclass
class VisualElement:
    concept: str
    description: str
    priority: int
    inclusion_requirement: bool
```

#### CompositionGuidelines
**Layout and composition rules**:
```python
@dataclass
class CompositionGuidelines:
    layout_type: str  # rule_of_thirds, centered, asymmetrical
    focal_points: List[str]
    depth_of_field: str
    perspective: str
    negative_space: str
```

#### ImageMetadata
**Generated image metadata**:
```python
@dataclass
class ImageMetadata:
    width: int
    height: int
    format: str
    size_bytes: int
    aspects_ratio: float
    file_path: Optional[str]
    cloud_storage_path: Optional[str]
```

#### BrandAlignmentScore
**Brand compliance measurement**:
```python
@dataclass
class BrandAlignmentScore:
    overall_score: float
    elements_checked: List[str]
    scores: Dict[str, float]
    issues: List[str]
```

#### PlatformSuitabilityScore
**Platform compatibility measurement**:
```python
@dataclass
class PlatformSuitabilityScore:
    overall_score: float
    criteria: List[str]
    scores: Dict[str, float]
    requirements_met: List[str]
    requirements_failed: List[str]
```

## Design Notes

### Artifact Flow

The data model enforces a strict sequential flow:
1. **GenerationContext**: Complete input data
2. **StrategyArtifact**: Planning and strategy decisions
3. **CopyArtifact**: Content generation
4. **ImagePromptArtifact**: Visual prompt creation
5. **ImageArtifact**: Final visual asset generation
6. **ValidationArtifact**: Quality assurance and compliance

Each subsequent artifact is generated from the previous one, ensuring traceability and dependency management.

### Validation Integration

Validation is embedded throughout the pipeline:
- StrategyArtifact → ValidationArtifact
- CopyArtifact → ValidationArtifact
- ImagePromptArtifact → ValidationArtifact
- ImageArtifact → ValidationArtifact

Validation results are stored as optional fields, allowing for partial success scenarios while maintaining audit trails.

### Naming Conventions

- Use `CamelCase` for all class names
- Use `snake_case` for all field names
- Include optional imports at the top-level module
- Use `Optional[...]` for fields that can be `None`
- Use `field(default_factory=...)` for complex default values
- Implement `to_dict()` and `from_dict()` serialization methods for all entities

### Serialization

All entities must support:
- `to_dict()`: Convert to plain dictionary for storage/transmission
- `from_dict()`: Reconstruct from dictionary
- `json()` and `from_json()`: JSON-specific serialization methods