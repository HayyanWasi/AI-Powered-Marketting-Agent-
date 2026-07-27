# Research for AI Generation Engine Module

## NEED CLARIFICATION

- **Technology approach for AI generation**: What specific AI libraries, frameworks, and APIs should be used for text generation (LLM), image generation (Pollinations), and content validation?

- **API endpoint contracts**: What are the exact HTTP interfaces and request/response shapes for the public module operations (BuildGenerationContext, GenerateStrategy, etc.)?

- **Integration patterns**: How does the module interact with the existing Campaign Management, Workflow Engine, and Operations modules through its public interfaces?

- **Mock strategies for external providers**: What mock implementations should be created for LLM providers, Pollinations AI, and validation services to enable deterministic testing?

- **Validation rule implementation**: How should content validation rules be defined and enforced for platform-specific compliance?

- **Testing fixtures and data**: What test data fixtures are needed for different input scenarios (complete context, incomplete context, conflicting guidelines, edge cases)?

- **Error handling strategies**: How should validation errors, generation failures, and API errors be structured and returned?

- **Performance monitoring**: What metrics should be tracked for generation pipeline performance without implementing observability directly?

## DEPENDENCIES

- **External services**: LLM Provider (Gemini/OpenAI), Pollinations AI, Validation Rules

- **Technology stack**: Python 3.13, FastAPI, supabase (Python SDK), pydantic v2, httpx, Pillow (PIL), openai, google-generativeai, duckduckgo-search

## BEST PRACTICES

- **Deterministic pipeline**: Linear execution where each stage consumes previous stage output
- **Immutable artifacts**: Artifacts should not be modified after creation
- **Stateless execution**: Module should not retain state between calls
- **Independent interfaces**: Each operation (BuildGenerationContext, GenerateStrategy, etc.) should be independently callable
- **Mock external APIs**: All AI providers should be mocked for deterministic testing

## INTEGRATION PATTERNS

- **Module boundaries**: Clear separation between AI Generation Engine and Campaign Management, Workflow Engine, Operations modules
- **Public interfaces**: Module exposes only the 6 operations listed in the spec
- **Artifact flow**: Sequential transformation through immutable artifacts
- **Error propagation**: Validation errors returned through ValidationArtifact without retries

## DECISIONS

- **LLM Provider**: Both OpenAI and Google Gemini available, use config-driven selection
- **Image Generation**: Pollinations AI for image generation with brand guidelines
- **Validation Rules**: Externalized validation rules with module-specific business logic
- **Error Format**: Structured validation errors with actionable messages
- **Testing Strategy**: Unit tests for each service with integration tests for full pipeline