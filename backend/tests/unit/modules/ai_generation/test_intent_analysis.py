"""Unit test for AI Generation Engine strategy analysis."""


class TestIntentAnalysis:
    """Test Intent Analyzer functionality."""

    def test_analyze_full_generation_intent_no_instructions(self):
        """Test intent analysis when no instructions provided."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        result = analyzer.analyze_regeneration_intent(
            {"strategy": "strategy_id", "copy": "copy_id", "image": "image_id"}, None
        )

        assert result["intent"] == "full_generation"
        assert result["mode"] == "complete"
        assert "No user instructions provided" in result["reason"]
        assert "preserve_artifacts" in result

    def test_analyze_text_regeneration_intent_with_changes(self):
        """Test intent analysis when text changes requested."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        user_instructions = {
            "user_intent": {
                "type": "copy_modification",
                "copy_modifications": {"headline": True, "body": True},
            },
            "changes": ["text"],
            "platforms": ["linkedin", "twitter"],
        }

        result = analyzer.analyze_regeneration_intent(
            {"strategy": "strategy_id", "copy": "copy_id", "image": "image_id"}, user_instructions
        )

        assert result["intent"] == "text_regeneration"
        assert result["mode"] == "copy_only"
        assert "text" in result["reason"].lower()
        assert result["preserve_artifacts"]["strategy"] == True
        assert result["preserve_artifacts"]["images"] == True
        assert "text_instructions" in result

    def test_analyze_image_regeneration_intent_with_changes(self):
        """Test intent analysis when image changes requested."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        user_instructions = {
            "user_intent": {
                "type": "visual_style_modification",
                "visual_style_changes": ["color_palette", "style"],
            },
            "changes": ["image"],
            "platforms": ["instagram"],
        }

        result = analyzer.analyze_regeneration_intent(
            {"strategy": "strategy_id", "copy": "copy_id", "image": "image_id"}, user_instructions
        )

        assert result["intent"] == "image_regeneration"
        assert result["mode"] == "image_only"
        assert "image" in result["reason"].lower()
        assert result["preserve_artifacts"]["strategy"] == True
        assert result["preserve_artifacts"]["copy"] == True
        assert "image_instructions" in result

    def test_analyze_strategy_revision_intent(self):
        """Test intent analysis when strategy revision requested."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        user_instructions = {
            "user_intent": {"type": "strategy_revision", "campaign_goals_revisions": ["goals"]},
            "changes": ["campaign_goals", "audience"],
            "platforms": ["linkedin", "instagram", "twitter"],
        }

        result = analyzer.analyze_regeneration_intent(
            {"strategy": "strategy_id", "copy": "copy_id", "image": "image_id"}, user_instructions
        )

        assert result["intent"] == "strategy_revision"
        assert result["mode"] == "strategy_first"
        assert "strategy" in result["reason"].lower()
        assert result["preserve_artifacts"] == False
        assert "strategy_instructions" in result

    def test_extract_text_instructions_from_copy_modifications(self):
        """Test text instruction extraction from copy modifications."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        user_intent = {
            "copy_modifications": {
                "tone": "more_professional",
                "length": "shorter",
            },
            "platforms": ["linkedin", "twitter"],
        }

        result = analyzer._extract_text_instructions(user_intent)

        assert result is not None
        assert result["type"] == "copy_modification"
        assert "tone" in result["modifications"]
        assert "length" in result["modifications"]
        assert result["platforms"] == ["linkedin", "twitter"]

    def test_extract_text_instructions_from_headline_changes(self):
        """Test text instruction extraction from headline changes."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        user_intent = {
            "headline_changes": ["New tech highlights", "Updated benefits"],
            "platforms": ["instagram", "facebook"],
        }

        result = analyzer._extract_text_instructions(user_intent)

        assert result is not None
        assert result["type"] == "text_content_modification"
        assert "headline_changes" in result
        assert result["platforms"] == ["instagram", "facebook"]

    def test_extract_image_instructions_from_visual_style_changes(self):
        """Test image instruction extraction from visual style changes."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        user_intent = {
            "visual_style_changes": {
                "artistic_style": "modern_tech",
                "color_palette": ["#FF0000", "#00FF00"],
            },
            "platforms": ["instagram"],
        }

        result = analyzer._extract_image_instructions(user_intent)

        assert result is not None
        assert result["type"] == "visual_style_modification"
        assert "visual_style_changes" in result
        assert result["platforms"] == ["instagram"]

    def test_extract_image_instructions_from_color_changes(self):
        """Test image instruction extraction from color palette changes."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        user_intent = {
            "color_palette_changes": {
                "primary": "#0000FF",
                "secondary": "#FFFF00",
            },
            "platforms": ["linkedin", "facebook"],
        }

        result = analyzer._extract_image_instructions(user_intent)

        assert result is not None
        assert result["type"] == "aesthetic_modification"
        assert "color_palette_changes" in result

    def test_extract_strategy_instructions_from_campaign_goals(self):
        """Test strategy instruction extraction from campaign goals."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        user_intent = {
            "campaign_goals_revisions": ["increase leads by 50%", "improve brand awareness"],
            "audience_changes": ["enterprise customers", "SMBs"],
            "platforms": ["linkedin", "instagram"],
        }

        result = analyzer._extract_strategy_instructions(user_intent)

        assert result is not None
        assert result["type"] == "strategy_revision"
        assert "campaign_goals_revisions" in result
        assert "audience_changes" in result
        assert result["platforms"] == ["linkedin", "instagram"]

    def test_validate_intent_analysis_with_valid_result(self):
        """Test intent analysis validation with valid result."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        intent_result = {
            "intent": "text_regeneration",
            "mode": "copy_only",
            "reason": "User requests text copy regeneration",
            "preserve_artifacts": {"strategy": True, "images": True},
            "text_instructions": {"modifications": {"tone": "professional"}},
        }

        generation_context = {"strategy": "strategy_id", "copy": "copy_id", "image": "image_id"}

        result = analyzer.validate_intent_analysis(intent_result, generation_context)

        assert "intent" in result["validated_by"].lower()
        assert result["compliance_scores"]["analysis_completeness"] > 0

    def test_validate_intent_analysis_with_missing_fields(self):
        """Test intent analysis validation with missing fields."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        intent_result = {"mode": "copy_only", "reason": "Test"}

        generation_context = {
            "strategy": None,
        }

        result = analyzer.validate_intent_analysis(intent_result, generation_context)

        assert result["is_valid"] is False
        assert any(
            error.get("code") == "MISSING_INTENT"
            or getattr(error, "code", None) == "MISSING_INTENT"
            for error in result["errors"]
        )

    def test_validate_intent_analysis_with_strategy_preservation_warnings(self):
        """Test intent analysis validation with preservation warnings."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        intent_result = {
            "intent": "text_regeneration",
            "mode": "copy_only",
            "reason": "Test",
            "preserve_artifacts": {"strategy": True, "images": True},
        }

        generation_context = {"strategy": None, "copy": "copy_id", "image": "image_id"}

        result = analyzer.validate_intent_analysis(intent_result, generation_context)

        assert result["is_valid"] is True  # Warnings do not make is_valid False
        assert any("strategy" in str(warning).lower() for warning in result["warnings"])

    def test_intent_analysis_edge_cases(self):
        """Test edge cases in intent analysis."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        # Test with empty user instructions
        result = analyzer.analyze_regeneration_intent({"strategy": "test"}, {})
        assert result["intent"] == "full_generation"

        # Test with empty user_intent
        user_instructions = {
            "user_intent": {},
            "changes": ["random change"],
        }
        result = analyzer.analyze_regeneration_intent(
            {"strategy": "test", "copy": "test", "image": "test"}, user_instructions
        )
        # Should default to full generation since no clear intent
        assert result["intent"] == "full_generation"

    def test_intent_analysis_deterministic_behavior(self):
        """Test that intent analysis produces deterministic results."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        user_instructions = {
            "user_intent": {"type": "copy_modification"},
            "changes": ["headline"],
            "platforms": ["linkedin"],
        }

        context = {"strategy": "test", "copy": "test", "image": "test"}

        # Call twice with same input
        result1 = analyzer.analyze_regeneration_intent(context, user_instructions)
        result2 = analyzer.analyze_regeneration_intent(context, user_instructions)

        # Results should be identical
        assert result1["intent"] == result2["intent"]
        assert result1["mode"] == result2["mode"]
        assert result1["reason"] == result2["reason"]

    def test_intent_analysis_metadata_inclusion(self):
        """Test that intent analysis includes metadata."""
        from src.modules.ai_generation.services.intent_analyzer import IntentAnalyzerService

        analyzer = IntentAnalyzerService()

        user_instructions = {
            "user_intent": {"type": "full_content_update"},
        }

        context = {"strategy": "test", "copy": "test", "image": "test"}

        result = analyzer.analyze_regeneration_intent(context, user_instructions)

        assert "timestamp" in result
        assert result["timestamp"] is not None
        assert isinstance(result["timestamp"], str)
        assert len(result["timestamp"]) > 10
