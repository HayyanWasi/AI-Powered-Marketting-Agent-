# Feature Specification: LLM Integration Service

**Feature Branch**: `006-llm-service`  
**Phase**: Core Services
**Created**: 2026-07-15  
**Status**: Draft  
**Input**: Unified interface for OpenAI GPT-4o and Google Gemini LLMs with system prompt management.

## User Scenarios & Testing

### User Story 1 - Generate Text via Default LLM Provider (Priority: P1)

As a Campaign Agent developer, I want to send a text prompt to the default LLM provider (OpenAI) and receive a generated response so that I can integrate LLM capabilities into campaign generation logic.

**Why this priority**: This is the core value — without basic text generation, no campaign agent can function.

**Independent Test**: Can be fully tested by calling the unified interface with a simple prompt and verifying a text response is returned with expected content structure.

**Acceptance Scenarios**:

1. **Given** the system is configured with an active OpenAI API key, **When** a developer sends a text prompt through the unified interface, **Then** the system shall return a generated text response from GPT-4o.
2. **Given** the OpenAI API returns an error (timeout, rate limit, server error), **When** the unified interface receives the failure, **Then** the system shall automatically retry with exponential backoff (up to 3 attempts).
3. **Given** all OpenAI retries are exhausted, **When** the unified interface detects the failure, **Then** the system shall automatically fall back to Gemini for that request and return the Gemini-generated response.
4. **Given** both OpenAI and Gemini fail, **When** the request completes, **Then** the system shall raise a meaningful error indicating both providers are unavailable.

---

### User Story 2 - Stream Text from LLM (Priority: P2)

As a Campaign Agent developer, I want to stream token-by-token responses from the LLM so that I can provide real-time feedback to users during long generations.

**Why this priority**: Streaming is critical for user experience during long campaign text generation but is not required for the initial integration.

**Independent Test**: Can be fully tested by calling the streaming interface with a prompt and verifying that multiple partial responses are received before the final complete response.

**Acceptance Scenarios**:

1. **Given** a streaming request is made to the unified interface, **When** the provider begins generating, **Then** the system shall yield partial tokens as they arrive.
2. **Given** a streaming request is in progress, **When** the primary provider fails mid-stream, **Then** the system shall not fall back — the error is propagated to the caller.

---

### User Story 3 - Use Named System Prompt Templates (Priority: P2)

As a Campaign Agent developer, I want to select a named system prompt template and inject variables into it so that each campaign type gets consistent, tailored instructions without duplicating prompt logic.

**Why this priority**: Named templates reduce duplication and ensure consistent prompting across campaign types, but basic string-based system prompt injection is sufficient for initial use.

**Independent Test**: Can be fully tested by defining a named template with variable placeholders, calling the interface with the template name and variables, and verifying the system prompt is correctly rendered before being sent to the LLM.

**Acceptance Scenarios**:

1. **Given** a named prompt template exists with placeholders for variables (e.g., `{guest_name}`, `{company_tone}`), **When** a developer calls the interface with that template name and variable values, **Then** the system shall render the template by substituting the provided variables.
2. **Given** a developer provides a template name that does not exist, **When** the interface processes the request, **Then** the system shall return an error indicating the template was not found.
3. **Given** required template variables are missing from the request, **When** the interface processes the request, **Then** the system shall leave unreplaced placeholders as-is (no crash, no silent omission).

---

### User Story 4 - Track Token Usage (Priority: P3)

As a system administrator, I want token counts returned with each LLM response so that I can monitor usage and estimate costs.

**Why this priority**: Usage tracking is important for cost governance but is not critical for initial functionality.

**Independent Test**: Can be fully tested by sending a known prompt and verifying the response includes prompt tokens, completion tokens, and total tokens.

**Acceptance Scenarios**:

1. **Given** any LLM response is generated, **When** the response is returned by the unified interface, **Then** the response shall include prompt token count, completion token count, and total token count.
2. **Given** a streaming response completes, **When** the final aggregated response is delivered, **Then** the response shall include cumulative token counts for the entire streamed exchange.

---

### Edge Cases

- Both providers are exhausted by rate limits simultaneously — request fails gracefully.
- Streaming response from Gemini has different chunking behavior than OpenAI — interface normalizes the streaming contract.
- Token counting for Gemini models uses different tokenization than OpenAI — counts are provider-native and clearly labeled.
- Template variable contains special characters (HTML, markdown) — not escaped, passed through as-is.
- Provider API key is missing or invalid at startup — error is deferred to first request (lazy initialization).
- Multiple concurrent requests to the same provider — handled; no rate limit coordination across requests (caller manages concurrency).

## Requirements

### Functional Requirements

- **FR-01**: The system shall provide a unified interface that supports both OpenAI GPT-4o and Google Gemini as LLM providers. Both providers shall accept the same prompt structure and return the same response structure.
- **FR-02**: The system shall use OpenAI as the primary provider and Google Gemini as the fallback provider. If OpenAI succeeds, the response is returned immediately without calling Gemini.
- **FR-03**: The system shall implement retry logic with exponential backoff (3 attempts: 1s, 2s, 4s delays) for transient API failures (timeout, rate limit, 5xx errors). Non-retryable errors (auth failures, invalid requests) shall be propagated immediately.
- **FR-04**: The system shall support both standard (complete response) and streaming (token-by-token) generation modes through the unified interface.
- **FR-05**: The system shall support named system prompt templates with variable injection. Templates shall be stored in code (not a database) and referenced by name. Variables use `{variable_name}` syntax.
- **FR-06**: The system shall return token usage statistics (prompt tokens, completion tokens, total tokens) with every response, labeled by provider.
- **FR-07**: The system shall provide a mock/STUB implementation for testing that returns configurable responses without calling any external API.

### Dependencies and Assumptions

- This feature depends on the `openai` and `google-generativeai` SDK packages already installed in the project.
- Provider API keys are configured via environment variables (`OPENAI_API_KEY`, `GOOGLE_API_KEY`) managed by the existing `Settings` class.
- Token counting uses the provider's native tokenizer — no custom tokenization logic is implemented.
- Named templates are defined in Python code (not stored in a database or file system).
- The fallback provider is called only when the primary provider's retries are fully exhausted and the error is transient.

### Business Rules

- Fallback to Gemini occurs only for transient failures (timeout, rate limit, server error). Authentication errors on OpenAI do not trigger fallback.
- Streaming mode does not support provider fallback — if the streaming provider fails mid-stream, the error is propagated to the caller.
- Template names are case-sensitive and must match exactly.

### Key Entities

- **LLM Provider**: Represents an external LLM service (OpenAI or Gemini). Each provider wraps its own SDK and normalizes the request/response format to a common interface.
- **System Prompt Template**: A named, parameterized prompt string with `{variable}` placeholders that is rendered with provided variable values before being sent to the LLM.
- **LLM Response**: A normalized response object containing the generated text, token usage statistics, and provider metadata.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Text generation from either provider returns a response within 30 seconds under normal network conditions.
- **SC-002**: Automatic fallback to Gemini succeeds within 5 seconds of OpenAI's final retry exhaustion.
- **SC-003**: All provider errors produce meaningful, user-facing error messages that identify the failing provider and the nature of the failure.
- **SC-004**: The unified interface can be swapped between providers without changing any calling code — only the provider configuration changes.
- **SC-005**: Token usage reporting is accurate to within the provider's own reported counts (validated by comparing to provider dashboard).
