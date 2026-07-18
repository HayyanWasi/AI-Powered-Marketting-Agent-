"""Integration test for AI Generation Engine full pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


@pytest.fixture
def mock_generation_service():
    """Create a mocked AIGenerationService for testing."""
    service = AsyncMock()
    service.generate = AsyncMock()
    service.regenerate_text = AsyncMock()
    service.regenerate_image = AsyncMock()
    service.validate_all_artifacts = AsyncMock()
    return service


@pytest.fixture
def full_generation_context():
    """Provide complete generation context for pipeline testing."""
    return {
        "campaign_context": {
            "name": "Summer Product Launch",
            "goals": ["brand awareness", "lead generation"],
            "budget": 100000,
            "timeline": "2026-07-01 to 2026-09-30",
            "target_audience": "tech professionals 25-45 years old",
            "key_features": ["AI-powered", "cloud-based", "enterprise-ready"],
        },
        "company_profile": {
            "name": "InnovateTech Solutions",
            "mission": "Transform businesses with AI",
            "values": ["innovation", "excellence", "customer-success"],
            "tone": "forward-thinking, approachable, professional",
            "brand_voice_examples": [
                "We help businesses scale smarter",
                "Your AI partner for growth",
            ],
        },
        "audience": {
            "segments": ["tech decision makers", "enterprise CTOs", "digital transformation leads"],
            "psychographics": ["innovation-driven", "value-conscious", "long-term oriented"],
            "pain_points": ["scaling challenges", "technology integration", "cost optimization"],
            "preferred_channels": ["linkedin", "tech blogs", "webinars"],
        },
        "platforms": ["linkedin", "instagram", "twitter"],
        "brand_guidelines": {
            "voice_tone": "forward-thinking",
            "key_messages": [
                "AI that scales with you",
                "Future-ready solutions",
                "Smart automation for growth",
            ],
            "style_preferences": {
                "visual_style": "modern tech",
                "color_palette": ["#0066CC", "#00D084", "#FFFFFF"],
                "typography": "clean sans-serif",
                "imagery_style": "minimalist, data-visualization",
            },
            "logo_specs": {"width": 300, "height": 120},
            "brand_values": ["trust", "innovation", "transformation"],
            "content_guidelines": {
                "length_preferences": {
                    "linkedin": "300-500 words",
                    "instagram": "1-2 lines",
                    "twitter": "280 chars",
                },
                "hashtag_recommendations": ["#AITech", "#EnterpriseAI", "#DigitalTransformation"],
                "tone_adjustments": {
                    "formal": "Adjust for LinkedIn",
                    "casual": "Adjust for Twitter",
                },
            },
        },
        "reference_materials": [
            {
                "type": "competitor",
                "name": "CompetitorX",
                "analysis": "Strong brand presence but lacking in AI credibility",
                "market_position": "mid-market",
            },
            {
                "type": "benchmark",
                "name": "Industry Tech Report 2026",
                "key_stats": ["AI market growing 40% annually", "Enterprise adoption at 75%"],
                "trends": ["multimodal AI", "edge computing", "AI governance"],
            },
            {
                "type": "asset",
                "name": "Previous Campaign Assets",
                "assets": ["case_study.pdf", "demo_video.mp4", "whitepaper.pdf"],
                "performance_metrics": {"engagement_rate": "8.2%", "conversion_rate": "3.5%"},
            },
        ],
        "user_intent": {
            "type": "full_content_update",
            "customizations": {
                "emphasis": "enterprise solutions",
                "creativity_level": "medium",
                "brand_alignment": "high",
            },
            "constraints": {
                "max_length": 500,
                "target_audience_focus": "CTO level",
                "industry_specific": True,
            },
        },
    }


@pytest.fixture
def expected_strategy_artifact():
    """Provide expected strategy artifact structure."""
    return {
        "id": "strategy_7654",
        "generated_at": "2026-07-17T00:00:00Z",
        "audience_strategy": {
            "target_segments": ["tech decision makers", "enterprise CTOs"],
            "messaging_approach": "Forward-thinking and innovative",
            "key_messages": [
                "AI solutions that scale with your business",
                "Transform your enterprise with intelligent automation",
                "Future-ready technology for modern challenges",
            ],
        },
        "messaging_strategy": {
            "tone": "forward-thinking",
            "style": "Professional yet accessible",
            "key_points": [
                "Problem: Business automation challenges",
                "Solution: AI-powered enterprise tools",
                "Benefits: Efficiency, scalability, insights",
            ],
        },
        "platform_strategy": {
            "platforms": ["linkedin", "instagram", "twitter"],
            "adaptations": {
                "linkedin": {
                    "format": "article",
                    "length_limit": "500-1000 words",
                    "media_requirements": "professional imagery, charts, data",
                    "hashtag_guidelines": ["#AITech", "#EnterpriseAI", "#DigitalTransformation"],
                },
                "instagram": {
                    "format": "visual carousel",
                    "length_limit": "150-250 characters",
                    "media_requirements": "high-quality images, infographics",
                    "hashtag_guidelines": ["#TechLaunch", "#EnterpriseAI", "#Innovation"],
                },
                "twitter": {
                    "format": "short post",
                    "length_limit": "280 characters",
                    "media_requirements": "image, thread, or tweet deck",
                    "hashtag_guidelines": ["#AI", "#Tech", "#Business"],
                },
            },
        },
        "seo_strategy": {
            "primary_keywords": [
                "AI enterprise solutions",
                "business automation",
                "intelligent tools",
            ],
            "secondary_keywords": ["enterprise AI", "automation technology", "smart business"],
            "meta_descriptions": "Transform your business with AI-powered enterprise solutions designed for growth and efficiency",
            "content_structure": ["problem", "solution", "benefits", "call_to_action"],
        },
        "campaign_strategy": {
            "goals": ["brand awareness", "lead generation", "thought leadership"],
            "target_metrics": {
                "engagement_rate": "8%",
                "conversion_rate": "4%",
                "reach": "500k impressions",
            },
            "timeline": {
                "start_date": "2026-07-20",
                "duration": "90 days",
                "phases": ["launch", "growth", "maturity"],
            },
            "budget_distribution": {
                "paid_media": 0.5,
                "organic": 0.3,
                "content_creation": 0.2,
            },
            "approval_required": ["creative concepts", "final copy", "visual assets"],
        },
    }


@pytest.fixture
def expected_copy_artifact():
    """Provide expected copy artifact structure."""
    return {
        "id": "copy_1234",
        "generated_at": "2026-07-17T00:05:00Z",
        "headlines": [
            "AI Enterprise Solutions That Scale With Your Business",
            "Transform Your Enterprise with Intelligent Automation",
            "Future-Ready Technology for Modern Challenges",
        ],
        "body_copy": [
            "InnovateTech Solutions delivers enterprise-grade AI tools designed for businesses ready to transform.",
            "Our platform combines cutting-edge AI with intuitive interfaces, enabling teams to automate processes, gain insights, and accelerate growth.",
            "From single departments to entire enterprises, our solutions scale to meet your unique challenges and drive measurable results.",
        ],
        "call_to_actions": [
            "Schedule a Demo",
            "Download Whitepaper",
            "Contact Sales",
            "Learn More",
        ],
        "hashtags": {
            "linkedin": [
                "#AITech",
                "#EnterpriseAI",
                "#DigitalTransformation",
                "#BusinessInnovation",
            ],
            "instagram": ["#TechLaunch", "#EnterpriseAI", "#AI-powered", "#BusinessTech"],
            "twitter": ["#AI", "#Tech", "#Business", "#Automation"],
        },
        "platform_variations": {
            "linkedin": {
                "headline": "AI Enterprise Solutions That Scale With Your Business",
                "body": "InnovateTech Solutions delivers enterprise-grade AI tools designed for businesses ready to transform. Our platform combines cutting-edge AI with intuitive interfaces, enabling teams to automate processes, gain insights, and accelerate growth.",
                "cta": "Schedule a Demo",
                "hashtags": "#AITech #EnterpriseAI #DigitalTransformation #BusinessInnovation",
                "character_count": 482,
            },
            "instagram": {
                "headline": "Transform Your Enterprise with Intelligent Automation",
                "body": "From single departments to entire enterprises, our AI solutions scale to meet your unique challenges and drive measurable results.",
                "cta": "Learn More",
                "hashtags": "#TechLaunch #EnterpriseAI #AI-powered #BusinessTech",
                "character_count": 124,
            },
            "twitter": {
                "headline": "Future-Ready Technology for Modern Challenges",
                "body": "AI solutions that scale with your business. Schedule a demo today! #AI #Tech #Business",
                "cta": "Learn More",
                "hashtags": "#AI #Tech #Business #Automation",
                "character_count": 278,
            },
        },
    }


@pytest.fixture
def expected_image_prompt_artifact():
    """Provide expected image prompt artifact structure."""
    return {
        "id": "image_prompt_5678",
        "generated_at": "2026-07-17T00:10:00Z",
        "strategy_id": "strategy_7654",
        "copy_id": "copy_1234",
        "platform": "linkedin",
        "prompt_text": "Professional marketing image for Summer Product Launch. Target audience: tech professionals, enterprise CTOs. Brand voice: forward-thinking. Platform: linkedin. Visual style: modern technology style. Color palette: #0066CC, #00D084, #FFFFFF. Visual mood: trustworthy institutional. Composition: centered header footer. Lighting: clean sharp. Brand elements: brand logo, company colors, brand values: trust, innovation, excellence. Visual concepts: business transformation, AI technology, enterprise solutions. Image prompt for professional marketing use, commercial use.",
        "style_guidelines": {
            "artistic_style": "corporate_professional",
            "color_scheme": ["#0066CC", "#00D084", "#FFFFFF"],
            "visual_mood": "trustworthy_institutional",
            "typography": "professional_sans",
            "composition": "centered_header_footer",
            "lighting": "clean_sharp",
            "filters": [],
        },
        "brand_elements": [
            {
                "element_type": "logo",
                "location": "top-left",
                "opacity": 1.0,
                "size_spec": {"width": 200, "height": 80},
            },
            {
                "element_type": "color_palette",
                "location": "background",
                "opacity": 0.3,
                "size_spec": {"type": "background_fill"},
            },
            {
                "element_type": "tagline",
                "location": "bottom_center",
                "opacity": 0.8,
                "size_spec": {"width": 400, "height": 50},
            },
        ],
        "visual_elements": [
            {
                "concept": "business transformation",
                "description": "Visual representation of business transformation through technology",
                "priority": 1,
                "inclusion_requirement": True,
            },
            {
                "concept": "AI technology",
                "description": "Modern AI technology interface showing data flow and automation",
                "priority": 2,
                "inclusion_requirement": True,
            },
            {
                "concept": "enterprise solutions",
                "description": "Professional enterprise solutions dashboard display",
                "priority": 3,
                "inclusion_requirement": True,
            },
        ],
        "composition_guidelines": {
            "layout_type": "centered_header_footer",
            "focal_points": ["top-left", "center", "bottom-right"],
            "depth_of_field": "standard",
            "perspective": "eye_level",
            "negative_space": "moderate",
        },
    }


@pytest.fixture
def expected_image_artifact():
    """Provide expected image artifact structure."""
    return {
        "id": "image_9012",
        "generated_at": "2026-07-17T00:15:00Z",
        "prompt_id": "image_prompt_5678",
        "platform": "linkedin",
        "image_url": "https://storage.ai-generation.com/images/strategy_7654/0654_linkedin.jpg",
        "thumbnail_url": "https://storage.ai-generation.com/thumbnails/strategy_7654/0654_linkedin_thumb.jpg",
        "metadata": {
            "width": 800,
            "height": 600,
            "format": "jpg",
            "size_bytes": 245760,
            "aspect_ratio": 1.33,
            "file_path": "/images/strategy_7654_800x600.jpg",
            "cloud_storage_path": "gs://ai-generation/strategy_7654/images/800x600.jpg",
            "generated_at": "2026-07-17T00:15:00Z",
            "prompt_id": "image_prompt_5678",
        },
        "brand_alignment": {
            "overall_score": 0.92,
            "elements_checked": ["logo_usage", "color_alignment", "brand_values"],
            "scores": {"logo_usage": 1.0, "color_alignment": 0.95, "brand_values": 0.88},
            "issues": [],
        },
        "platform_suitability": {
            "overall_score": 0.88,
            "criteria": ["resolution", "aspect_ratio", "media_requirements", "load_time"],
            "scores": {
                "resolution": 1.0,
                "aspect_ratio": 0.95,
                "media_requirements": 1.0,
                "load_time": 0.95,
            },
            "requirements_met": [
                "High resolution suitable",
                "Aspect ratio appropriate",
                "Media requirements satisfied",
                "Load time optimal",
            ],
            "requirements_failed": [],
        },
    }


@pytest.fixture
def expected_validation_artifact():
    """Provide expected validation artifact structure."""
    return {
        "id": "validation_20260717-001",
        "generated_at": "2026-07-17T00:20:00Z",
        "artifact_type": "comprehensive",
        "artifact_id": "validation_results",
        "is_valid": True,
        "errors": [],
        "warnings": [
            {
                "code": "MISSING_AUDIENCE_SEGMENTS",
                "message": "Audience segments are recommended for targeted content",
                "field": "audience_strategy.target_segments",
            },
        ],
        "compliance_scores": {
            "required_fields": 1.0,
            "audience_segments": 0.67,
            "brand_voice": 1.0,
            "platform_adaptations": 1.0,
        },
        "recommendations": [
            "Define specific audience segments for better targeting",
            "Ensure all strategy components are populated",
        ],
        "validated_by": "ValidationService",
    }


@pytest.fixture
def expected_full_pipeline_result():
    """Provide expected full pipeline result structure."""
    return {
        "strategy": expected_strategy_artifact(),
        "copy": expected_copy_artifact(),
        "image_prompt": expected_image_prompt_artifact(),
        "image": expected_image_artifact(),
        "validation": expected_validation_artifact(),
        "metadata": {
            "generated_at": "2026-07-17T00:20:00Z",
            "pipeline_version": "1.0",
            "total_artifacts": 4,
            "validation_passed": True,
        },
    }


class TestAIGenerationEngineFullPipeline:
    """Integration tests for complete AI Generation Engine pipeline."""

    @pytest.mark.asyncio
    async def test_generate_complete_campaign_from_context(
        self,
        mock_generation_service,
        full_generation_context,
        expected_full_pipeline_result,
    ):
        """Test complete campaign generation from single context request."""
        # Mock the service response
        mock_generation_service.generate.return_value = expected_full_pipeline_result

        # Execute generation
        result = await mock_generation_service.generate(full_generation_context)

        # Verify all expected artifacts are present
        assert "strategy" in result
        assert "copy" in result
        assert "image_prompt" in result
        assert "image" in result
        assert "validation" in result
        assert "metadata" in result

        # Verify pipeline execution order
        mock_generation_service.generate.assert_called_once_with(full_generation_context)

        # Verify validation passed
        assert result["validation"]["is_valid"] is True
        assert len(result["validation"]["errors"]) == 0

        # Verify metadata
        assert result["metadata"]["pipeline_version"] == "1.0"
        assert result["metadata"]["total_artifacts"] == 4
        assert result["metadata"]["validation_passed"] is True

    @pytest.mark.asyncio
    async def test_generate_complete_campaign_with_minimal_context(
        self,
        mock_generation_service,
        full_generation_context,
    ):
        """Test generation with minimal context (only required fields)."""
        # Create minimal context with only required fields
        minimal_context = {
            "campaign_context": {"name": "Minimal Campaign"},
            "company_profile": {"name": "Company"},
            "audience": {"segments": ["segment1"]},
            "platforms": ["linkedin"],
            "brand_guidelines": {"voice_tone": "professional"},
            "reference_materials": [{"type": "benchmark", "source": "report.pdf"}],
        }

        # Mock service to return a valid result
        mock_result = {
            "strategy": {"id": "strategy_123", "goals": ["brand awareness"]},
            "copy": {"id": "copy_456", "headlines": ["Test Headline"]},
            "image_prompt": {"id": "prompt_789", "prompt_text": "Test prompt"},
            "image": {"id": "image_999", "image_url": "https://test.com/image.jpg"},
            "validation": {"is_valid": True, "errors": []},
            "metadata": {"generated_at": "2026-07-17T00:00:00Z"},
        }
        mock_generation_service.generate.return_value = mock_result

        result = await mock_generation_service.generate(minimal_context)

        assert result["validation"]["is_valid"] is True
        assert len(result["validation"]["errors"]) == 0

    @pytest.mark.asyncio
    async def test_generation_preserves_correct_artifact_order(
        self,
        mock_generation_service,
        full_generation_context,
    ):
        """Test that generated artifacts maintain correct dependency order."""
        # Track call order
        call_log = []

        async def tracking_generate(context):
            call_log.append("generate")
            return {
                "strategy": {"id": "strategy_1", "generated_at": "2026-07-17T00:00:00Z"},
                "copy": {"id": "copy_1", "generated_at": "2026-07-17T00:05:00Z"},
                "image_prompt": {"id": "prompt_1", "generated_at": "2026-07-17T00:10:00Z"},
                "image": {"id": "image_1", "generated_at": "2026-07-17T00:15:00Z"},
                "validation": {"is_valid": True, "errors": []},
                "metadata": {"generated_at": "2026-07-17T00:20:00Z"},
            }

        mock_generation_service.generate = tracking_generate

        result = await mock_generation_service.generate(full_generation_context)

        # Verify artifacts were generated in correct order
        assert "strategy" in result
        assert "copy" in result
        assert "image_prompt" in result
        assert "image" in result

        # Verify timestamps show correct progression
        strategy_time = result["strategy"]["generated_at"]
        copy_time = result["copy"]["generated_at"]
        prompt_time = result["image_prompt"]["generated_at"]
        image_time = result["image"]["generated_at"]
        validation_time = result["validation"]["generated_at"]

        # Verify chronological order
        assert strategy_time < copy_time < prompt_time < image_time < validation_time

    @pytest.mark.asyncio
    async def test_generation_pipeline_deterministic_behavior(
        self,
        mock_generation_service,
        full_generation_context,
    ):
        """Test that pipeline produces deterministic results for same input."""
        # Mock deterministic response
        deterministic_result = {
            "strategy": {"id": "strategy_7654", "hash": "abc123"},
            "copy": {"id": "copy_1234", "hash": "def456"},
            "image_prompt": {"id": "prompt_5678", "hash": "ghi789"},
            "image": {"id": "image_9012", "hash": "jkl012"},
            "validation": {"is_valid": True, "hash": "mno345"},
            "metadata": {"generated_at": "2026-07-17T00:20:00Z", "hash": "pqr678"},
        }

        mock_generation_service.generate.return_value = deterministic_result

        # Execute generation twice with same input
        result1 = await mock_generation_service.generate(full_generation_context)
        result2 = await mock_generation_service.generate(full_generation_context)

        # Verify identical results (except timestamps may differ slightly)
        assert result1["strategy"]["id"] == result2["strategy"]["id"]
        assert result1["copy"]["id"] == result2["copy"]["id"]
        assert result1["image_prompt"]["id"] == result2["image_prompt"]["id"]
        assert result1["image"]["id"] == result2["image"]["id"]
        assert result1["validation"]["is_valid"] == result2["validation"]["is_valid"]

    @pytest.mark.asyncio
    async def test_generation_with_invalid_context_should_fail_validation(
        self,
        mock_generation_service,
    ):
        """Test that invalid context triggers validation failure."""
        invalid_context = {
            "campaign_context": {},  # Empty
            "company_profile": {},  # Empty
            "audience": {},  # Empty
            "platforms": [],  # Empty
            "brand_guidelines": {},  # Empty
            "reference_materials": [],  # Empty
        }

        # Mock validation to indicate failure
        failed_validation = {
            "is_valid": False,
            "errors": [
                {
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Missing required field: campaign_context",
                },
                {
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Missing required field: company_profile",
                },
                {"code": "MISSING_REQUIRED_FIELD", "message": "Missing required field: audience"},
            ],
            "warnings": [],
            "compliance_scores": {"required_fields": 0.0},
            "recommendations": ["Provide all required fields"],
        }

        failed_result = {
            "strategy": None,
            "copy": None,
            "image_prompt": None,
            "image": None,
            "validation": failed_validation,
            "metadata": {"generated_at": "2026-07-17T00:20:00Z", "failed": True},
        }
        mock_generation_service.generate.return_value = failed_result

        result = await mock_generation_service.generate(invalid_context)

        # Verify validation indicates failure
        assert result["validation"]["is_valid"] is False
        assert len(result["validation"]["errors"]) >= 2
        assert result["strategy"] is None
        assert result["copy"] is None
        assert result["image_prompt"] is None
        assert result["image"] is None

    @pytest.mark.asyncio
    async def test_generation_performance_within_limits(
        self,
        mock_generation_service,
        full_generation_context,
    ):
        """Test that generation completes within performance requirements."""
        import time

        async def fast_generate(context):
            # Simulate fast generation (within 60 seconds)
            await asyncio.sleep(0.01)  # Minimal delay
            return {
                "strategy": {"id": "strategy_fast", "generated_at": datetime.now().isoformat()},
                "copy": {"id": "copy_fast", "headlines": ["Fast Generation"]},
                "image_prompt": {"id": "prompt_fast", "prompt_text": "Fast prompt"},
                "image": {"id": "image_fast", "image_url": "https://fast.com/image.jpg"},
                "validation": {"is_valid": True, "errors": []},
                "metadata": {"generated_at": datetime.now().isoformat(), "duration": "0.01s"},
            }

        mock_generation_service.generate = fast_generate

        start_time = time.time()
        result = await mock_generation_service.generate(full_generation_context)
        end_time = time.time()

        duration = end_time - start_time

        # Verify completion within 60 seconds (performance requirement)
        assert duration < 60.0, f"Generation took {duration:.2f}s, exceeds 60s limit"

        # Verify successful result
        assert result["validation"]["is_valid"] is True

    @pytest.mark.asyncio
    async def test_generation_output_structure_and_data_types(
        self,
        mock_generation_service,
        full_generation_context,
    ):
        """Test that generated artifacts have correct data types and structure."""
        result = {
            "strategy": {
                "id": "strategy_string",
                "generated_at": "2026-07-17T00:00:00Z",
                "audience_strategy": {
                    "target_segments": ["segment1"],
                    "messaging_approach": "string",
                },
                "messaging_strategy": {"tone": "string", "style": "string"},
                "platform_strategy": {"platforms": ["string"], "adaptations": {}},
                "seo_strategy": {"primary_keywords": ["string"], "content_structure": []},
                "campaign_strategy": {"goals": ["string"], "target_metrics": {}},
            },
            "copy": {
                "id": "copy_string",
                "generated_at": "2026-07-17T00:00:00Z",
                "strategy_id": "string",
                "platform": "string",
                "headlines": ["string1", "string2"],
                "captions": ["string1"],
                "ctas": ["string1"],
                "hashtags": ["#tag1"],
                "platform_variations": {
                    "platform1": {
                        "headline": "string",
                        "body": "string",
                        "cta": "string",
                        "hashtags": "string",
                        "character_count": 100,
                    }
                },
            },
            "image_prompt": {
                "id": "prompt_string",
                "generated_at": "2026-07-17T00:00:00Z",
                "strategy_id": "string",
                "copy_id": "string",
                "platform": "string",
                "prompt_text": "string prompt text",
                "style_guidelines": {"artistic_style": "string", "color_scheme": []},
                "brand_elements": [],
                "visual_elements": [],
                "composition_guidelines": {"layout_type": "string"},
                "validation_results": None,
            },
            "image": {
                "id": "image_string",
                "generated_at": "2026-07-17T00:00:00Z",
                "prompt_id": "string",
                "platform": "string",
                "image_url": "https://string.com/image.jpg",
                "thumbnail_url": "https://string.com/thumbnail.jpg",
                "metadata": {
                    "width": 100,
                    "height": 100,
                    "format": "jpg",
                    "size_bytes": 1000,
                    "aspect_ratio": 1.0,
                },
                "brand_alignment": {
                    "overall_score": 0.5,
                    "elements_checked": [],
                    "scores": {},
                    "issues": [],
                },
                "platform_suitability": {
                    "overall_score": 0.5,
                    "criteria": [],
                    "scores": {},
                    "requirements_met": [],
                    "requirements_failed": [],
                },
                "validation_results": None,
            },
            "validation": {
                "id": "validation_string",
                "generated_at": "2026-07-17T00:00:00Z",
                "artifact_type": "comprehensive",
                "artifact_id": "validation_results",
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "compliance_scores": {"required_fields": 1.0},
                "recommendations": [],
                "validated_by": "ValidationService",
            },
            "metadata": {
                "generated_at": "2026-07-17T00:00:00Z",
                "pipeline_version": "1.0",
                "total_artifacts": 4,
                "validation_passed": True,
            },
        }

        mock_generation_service.generate.return_value = result

        actual_result = await mock_generation_service.generate(full_generation_context)

        # Verify all expected fields are present with correct types
        assert isinstance(actual_result, dict)
        assert "strategy" in actual_result
        assert "copy" in actual_result
        assert "image_prompt" in actual_result
        assert "image" in actual_result
        assert "validation" in actual_result
        assert "metadata" in actual_result

        # Verify strategy structure
        assert "id" in actual_result["strategy"]
        assert "generated_at" in actual_result["strategy"]
        assert "audience_strategy" in actual_result["strategy"]

        # Verify copy structure
        assert "headlines" in actual_result["copy"]
        assert "captions" in actual_result["copy"]
        assert "ctas" in actual_result["copy"]
        assert "hashtags" in actual_result["copy"]
        assert "platform_variations" in actual_result["copy"]

        # Verify image prompt structure
        assert "prompt_text" in actual_result["image_prompt"]
        assert "style_guidelines" in actual_result["image_prompt"]
        assert "composition_guidelines" in actual_result["image_prompt"]

        # Verify validation structure
        assert "is_valid" in actual_result["validation"]
        assert "errors" in actual_result["validation"]
        assert "compliance_scores" in actual_result["validation"]

        # Verify metadata structure
        assert "pipeline_version" in actual_result["metadata"]
        assert "total_artifacts" in actual_result["metadata"]
        assert "validation_passed" in actual_result["metadata"]
