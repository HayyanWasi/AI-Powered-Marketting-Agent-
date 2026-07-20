"""Quick Start Guide for AI Generation Engine Module"""

# AI Generation Engine Module

## Overview

The AI Generation Engine module provides a deterministic pipeline for generating marketing campaign assets through structured stages: context building, strategy planning, copy generation, image prompt creation, image generation, and validation.

## Key Features

### Independent Operations

The module exposes six independent public interfaces:

1. **BuildGenerationContext()** - Assembles complete campaign context from input data
2. **GenerateStrategy()** - Creates campaign strategy from context
3. **GenerateCopy()** - Generates platform-specific marketing copy
4. **GenerateImagePrompt()** - Creates image prompts from strategy and copy
5. **GenerateImage()** - Generates campaign images from prompts
6. **ValidateArtifacts()** - Validates all generated outputs against business rules

### Generation Pipeline

```
Generation Context
        │
        ▼
Strategy Artifact
        │
        ▼
Copy Artifact
        │
        ▼
Image Prompt Artifact
        │
        ▼
Image Artifact
        │
        ▼
Validation Artifact
```

### Artifact Flow

Each stage consumes the artifact produced by the previous stage, ensuring deterministic and traceable generation.

## Quick Start

### Prerequisites

- Python 3.13+
- FastAPI
- supabase (Python SDK)
- AI providers (OpenAI, Gemini, Pollinations)

### Installation

```bash
# Module is part of the AI Social Campaign Manager backend
# All dependencies are already installed in the project
uv sync
uv run pytest backend/tests/modules/ai_generation/
```

### Basic Usage Example

```python
from backend.src.modules.ai_generation import (
    ContextBuilderService,
    StrategyPlannerService,
    CopyGeneratorService,
    ImagePromptService,
    ImageGeneratorService,
    ValidationService,
)

# Initialize services
context_builder = ContextBuilderService()
strategy_planner = StrategyPlannerService()
copy_generator = CopyGeneratorService()
image_prompt = ImagePromptService()
image_generator = ImageGeneratorService()
validator = ValidationService()

# Example: Generate complete campaign
context = context_builder.build_generation_context(
    campaign_context={
        "name": "Q4 2026 Campaign",
        "goals": {"primary": "Increase engagement", "metrics": ["CTR", "conversion"]},
        "platforms": ["LinkedIn", "Instagram"],
    },
    company_profile={
        "name": "Your Company",
        "voice": "professional",
        "values": ["innovation", "integrity"],
    },
    audience={
        "segments": ["enterprise", "decision-makers"],
        "demographics": {"age_range": "35-55", "income": "high"},
    },
    platforms=["LinkedIn", "Instagram"],
    brand_guidelines={
        "voice_tone": "professional",
        "color_palette": ["#000000", "#FFFFFF"],
        "fonts": ["Arial", "Helvetica"],
    },
    reference_materials=[],
)

# Generate strategy
strategy = strategy_planner.generate_strategy(context)

# Generate copy for each platform
copy_artifacts = []
for platform in ["LinkedIn", "Instagram"]:
    copy = copy_generator.generate_copy(strategy, platform)
    copy_artifacts.append(copy)

# Generate image prompts
image_prompts = []
for platform in ["LinkedIn", "Instagram"]:
    prompt = image_prompt.generate_image_prompt(strategy, copy_artifacts[0], platform)
    image_prompts.append(prompt)

# Generate images
images = []
for prompt in image_prompts:
    image = image_generator.generate_image(prompt)
    images.append(image)

# Validate all artifacts
validation = validator.validate_all_artifacts({
    "strategy": strategy,
    "copy": copy_artifacts,
    "image_prompts": image_prompts,
    "images": images,
})

if validation.is_success():
    print("Campaign generation completed successfully!")
else:
    print(f"Validation failed with {validation.get_error_count()} errors")
    for error in validation.errors:
        print(f"  - {error.message}")
```

### Testing

Run unit tests to verify each component:

```bash
# Run unit tests for all modules
uv run pytest backend/tests/unit/modules/ai_generation/

# Run integration test for full pipeline
uv run pytest backend/tests/integration/test_ai_generation_full_pipeline.py
```

### Performance

- Complete campaign generation: ≤60 seconds (target)
- Stateless operation (no database access)
- Deterministic pipeline with immutable artifacts

### Regeneration Support

The module supports independent regeneration:

- **Text-only regeneration**: Preserve strategy and images, only regenerate copy
- **Image-only regeneration**: Preserve strategy and copy, only regenerate images
- **Strategy revision**: Regenerate all artifacts based on updated strategy

## Module Architecture

### Module Independence

The AI Generation Engine operates completely independently:

- **No Campaign CRUD**: Does not create, update, publish, or persist campaign records
- **No Workflow Orchestration**: Pure generation pipeline without retries or checkpoints
- **No Observability**: Metrics and tracing handled by Operations module
- **No Long-term Memory**: Each call is stateless and deterministic

### Error Handling

All public interfaces return structured validation errors without retrying failed operations. Recovery belongs to the Workflow module.

## Dependencies

External services (all mocked in testing):

- LLM Provider (OpenAI/Gemini)
- Pollinations AI (Image generation)
- Validation Rules (Business logic)

## Development

### Testing Strategy

1. **Unit Tests**: Test each service independently with mocked external APIs
2. **Integration Tests**: Test full pipeline with mocked dependencies
3. **Error Scenarios**: Test with incomplete context, conflicting guidelines, validation failures

### Code Structure

```
backend/src/modules/ai_generation/
├── interfaces/
│   ├── context_builder.py
│   ├── strategy_planner.py
│   ├── copy_generator.py
│   ├── image_prompt_editor.py
│   ├── image_generator.py
│   └── validator.py
│
├── services/
│   ├── context_builder_service.py
│   ├── strategy_planner_service.py
│   ├── copy_generator_service.py
│   ├── image_prompt_service.py
│   ├── image_generator_service.py
│   └── validation_service.py
│
├── models/
│   ├── generation_context.py
│   ├── strategy_artifact.py
│   ├── copy_artifact.py
│   ├── image_prompt_artifact.py
│   ├── image_artifact.py
│   └── validation_artifact.py
│
└── __init__.py
```

## Migration Guide

### From Previous Versions

The AI Generation Engine has been redesigned to follow the new module-first architecture with clear boundaries between modules. If you're migrating from a previous version:

1. **Public Interface**: All operations now require explicit input artifacts
2. **No State Management**: Remove any code that relied on module state
3. **Artifact Consistency**: Ensure your applications expect and handle the new artifact structure

## Next Steps

1. Review the data-model.md for complete artifact specifications
2. Check contracts/ for detailed API contracts and validation rules
3. Implement business logic in the service layer
4. Run comprehensive tests to ensure correctness
5. Integrate with Workflow Engine for orchestration