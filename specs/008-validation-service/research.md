# Content Validation Service - Research

## Overview
Research findings to inform the Content Validation Service specification and implementation.

## Decision: Project Structure

### Selected Structure: Backend-only with Validation Service

**Decision:** The Content Validation Service will be implemented as part of the existing backend system in `backend/src/services/image_validation_service.py` and potentially `backend/src/api/routes` as needed, rather than creating a separate service.

**Rationale:**
- Simplest implementation approach for initial release
- Leverages existing FastAPI backend structure
- Minimal architectural complexity
- Aligns with KISS principle (Principle III)
- Easier to test and maintain initially
- Reduces deployment complexity

**Alternatives Considered:**
1. **Standalone Validation Service:** Separate microservice with its own API
   - **Pros:** Isolated, can be scaled independently, cleaner separation
   - **Cons:** Higher complexity, network overhead, additional deployment steps
   - **Rejected Because:** Violates KISS principle, adds unnecessary complexity for V1

2. **Integrated Function within Campaign Service:** Function embedded within campaign generation
   - **Pros:** Tight coupling, simple to implement
   - **Cons:** Violates single responsibility, harder to test independently
   - **Rejected Because:** Requires separation of concerns for maintainability

3. **Message Queue System:** Asynchronous validation processing
   - **Pros:** Non-blocking, high throughput
   - **Cons:** Complex architecture, message queue infrastructure, testing overhead
   - **Rejected Because:** Over-engineering for initial release

### Validation Scope

**Decision:** Validation only evaluates, never modifies campaign content.

**Rationale:**
- Ensures predictable campaign generation
- Maintains clear boundaries between features
- Prevents recursive validation issues
- Aligns with "Validation never changes generated campaign content" requirement
- Simplies error handling

### Integration Points

**Decision:** Validation integrates into campaign generation pipeline immediately before campaign preview access.

**Rationale:**
- Early validation prevents wasted user effort
- Validates at the natural checkpoint where users view results
- Minimizes pipeline complexity
- Provides immediate feedback to users

## Research: Platform-Specific Validation Requirements

### Text Validation Requirements

**Decision:** Platform character limits are fixed requirements from spec:
- LinkedIn: 3000 characters or less
- Instagram: 2200 characters or less
- Facebook: ~63,206 characters (limit doesn't apply to validation)

**Rationale:** These are business requirements, not implementation details. The system must validate against these limits regardless of technical implementation.

### Image Validation Requirements

**Decision:** Minimum requirements from research:
- Resolution: Minimum 1080x1080 pixels (from constitution)
- Format: Common image formats (JPEG, PNG, WebP)
- File size: Reasonable limit to prevent abuse (~10MB)

**Rationale:** These are the industry-standard quality requirements for social media campaigns.

### Rule Structure Design

**Decision:** Validation rules will be structured as:
```
ValidationRule {
  rule_id: string,
  rule_type: 'TEXT' | 'IMAGE',
  platform: 'LinkedIn' | 'Instagram' | 'Facebook',
  name: string,                    // E.g., "Character Limit"
  description: string,             // E.g., "Character count must not exceed platform limit"
  validator: RuleValidator
  severity: 'ERROR' | 'WARNING'
}
```

**Rationale:**
- Clear, maintainable structure
- Supports different rule types
- Platform-specific validation
- Extensible for future rule types
- Easy to test individual rules

## Research: Error Handling & Reporting

### Validation Result Structure

**Decision:** Validation results will have:
```
ValidationResult {
  campaign_id: string,
  platform: string,
  validated_at: timestamp,
  text_validation: TextValidationResult,
  image_validation: ImageValidationResult,
  overall_status: 'PASS' | 'FAIL' | 'WARNING',
  error_count: number,
  message_count: number
}
```

**Rationale:**
- Comprehensive reporting
- Tracks which component (text/image) failed
- Provides aggregated status
- Maintains audit trail
- Clear for user interface

### Error Identification

**Decision:** Individual validation failures will report:
- Rule ID and name
- Error description
- Specific value that violated the rule
- Suggestion for correction when applicable

**Rationale:**
- Actionable user feedback
- Helps users understand and fix issues
- Supports self-service resolution
- Enables targeted corrections

## Research: Integration & Architecture

### Architecture Pattern

**Decision:** Linear pipeline validation (Principle IV - Fail gracefully):
1. Campaign content received
2. Platform determined
3. Validation rules loaded
4. Text validation executed
5. Image validation executed
6. Results compiled
7. Validation gateway checks results
8. Access granted/denied to preview

**Rationale:**
- Simple, predictable execution flow
- Easy to debug
- Maintains linear processing
- Consistent error handling
- Supports Principle V (Linear Pipeline)

### Performance Requirements

**Decision:** Validation must complete within same pipeline timing constraints:
- Validation time: < 5 seconds (acceptable for user experience)
- Throughput: Supports typical campaign generation pace
- Resource usage: Minimal CPU and memory footprint

**Rationale:**
- Maintains acceptable user experience
- Resource-efficient implementation
- Simple to optimize and measure
- Aligns with existing performance goals

## Research: Testing Strategy

### Test Coverage

**Decision:** Minimum 80% code coverage (Principle VI):
- Unit tests for each validation rule
- Integration tests for validation pipeline
- Mock tests for external dependencies
- End-to-end tests for complete workflow

**Rationale:**
- Ensures reliability
- Validates correctness
- Supports maintainability
- Meets project quality standards

### Test Scenarios

**Decision:** Test both success and failure cases:
- Valid content validation
- Text rule violations
- Image rule violations
- Mixed success/failure
- Edge cases and boundary conditions

**Rationale:**
- Comprehensive validation
- Robust error handling
- User experience coverage
- Reliable system behavior

## Research: Technology Selection

### Implementation Language

**Decision:** Python (as per project specification):
- Python 3.13+
- Pydantic v2 for validation schemas
- FastAPI for API endpoints
- Pillow for image processing
- pytest for testing

**Rationale:**
- Project standard technology
- Robust validation capabilities
- Well-documented frameworks
- Strong community support
- Aligns with project architecture

## Research: Dependencies & Infrastructure

### External Dependencies

**Decision:** Minimal dependency list for simplicity:
- **Pillow:** Image validation and processing
- **Pydantic v2:** Data validation and schema definition
- **FastAPI:** API framework (if adding endpoints)
- **Supabase:** Potential data storage needs

**Rationale:**
- Limited scope for initial implementation
- Reduces complexity
- Easier to maintain and test
- Faster initial release

### Testing Infrastructure

**Decision:** pytest with coverage plugin:
- Unit testing
- Integration testing
- Mock external dependencies
- Coverage reporting

**Rationale:**
- Project standard
- Comprehensive testing
- Coverage tracking
- Easy to integrate

## Research: Security & Best Practices

### Security Considerations

**Decision:** Validate input, never modify data, minimal permissions:
- Input validation for all campaign content
- Read-only access to campaign data
- Secure API key handling
- Error message sanitization

**Rationale:**
- Prevents injection attacks
- Maintains data integrity
- Protects sensitive information
- Follows security best practices

### Performance Best Practices

**Decision:** Lazy validation, efficient processing:
- Validate only necessary fields
- Cache rule definitions
- Optimize image processing
- Batch similar validations

**Rationale:**
- Improves performance
- Reduces resource usage
- Better user experience
- Scalable implementation

## Summary

The Content Validation Service research has identified clear implementation paths:

1. **Architecture:** Simple validation service within existing backend
2. **Technology:** Python + Pillow + Pydantic v2
3. **Rules:** Platform-specific text and image validation rules
4. **Integration:** Pipeline-based validation before preview access
5. **Testing:** Comprehensive unit, integration, and e2e tests
6. **Performance:** Sub-second validation times
7. **Security:** Input validation, no data modification
8. **Quality:** 80% code coverage, clean code principles

All "NEEDS CLARIFICATION" items from the technical context have been resolved. The specification is now ready for Phase 1 (Design & Contracts) with clear implementation guidance.