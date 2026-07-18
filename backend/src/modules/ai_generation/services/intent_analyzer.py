"""Intent analyzer service for AI Generation Engine."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..constants import SeverityLevel


class ValidationError:
    """Individual validation error."""

    def __init__(
        self,
        code: str,
        message: str,
        severity: str,
        field: Optional[str] = None,
        suggested_fix: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.severity = severity
        self.field = field
        self.suggested_fix = suggested_fix

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "field": self.field,
            "suggested_fix": self.suggested_fix,
        }


class ValidationWarning:
    """Individual validation warning."""

    def __init__(self, code: str, message: str, field: Optional[str] = None):
        self.code = code
        self.message = message
        self.field = field

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
        }


class IntentAnalyzerService:
    """Service for interpreting user regeneration requests."""

    def analyze_regeneration_intent(
        self,
        generation_context: Dict[str, Any],
        user_instructions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze user intent from generation context and instructions.

        Args:
            generation_context: Complete generation context with existing artifacts
            user_instructions: Optional instructions for regeneration

        Returns:
            Dict containing intent analysis and generation mode
        """
        if not user_instructions:
            return {
                "intent": "full_generation",
                "mode": "complete",
                "reason": "No user instructions provided - default to full generation",
                "timestamp": datetime.now().isoformat(),
            }

        user_intent = user_instructions.get("user_intent", {})
        regeneration_purpose = user_instructions.get("regeneration_purpose", "")

        # Analyze intent for full generation
        if (
            user_intent.get("type") == "full_content_update"
            or regeneration_purpose == "full_generation"
        ):
            return {
                "intent": "full_generation",
                "mode": "complete",
                "reason": "User requests full content regeneration",
                "timestamp": datetime.now().isoformat(),
                "preserve_artifacts": False,
            }

        # Analyze intent for text-only regeneration
        text_instructions = self._extract_text_instructions(user_intent)
        if text_instructions or any(
            "text" in str(instruction).lower() or "copy" in str(instruction).lower()
            for instruction in user_instructions.get("changes", [])
        ):
            return {
                "intent": "text_regeneration",
                "mode": "copy_only",
                "reason": "User requests text/copy regeneration only",
                "timestamp": datetime.now().isoformat(),
                "preserve_artifacts": {
                    "strategy": True,
                    "images": True,
                },
                "text_instructions": text_instructions,
            }

        # Analyze intent for image-only regeneration
        image_instructions = self._extract_image_instructions(user_intent)
        if image_instructions or any(
            "image" in str(instruction).lower() or "visual" in str(instruction).lower()
            for instruction in user_instructions.get("changes", [])
        ):
            return {
                "intent": "image_regeneration",
                "mode": "image_only",
                "reason": "User requests image regeneration only",
                "timestamp": datetime.now().isoformat(),
                "preserve_artifacts": {
                    "strategy": True,
                    "copy": True,
                },
                "image_instructions": image_instructions,
            }

        # Analyze intent for strategy revision
        strategy_instructions = self._extract_strategy_instructions(user_intent)
        if strategy_instructions:
            return {
                "intent": "strategy_revision",
                "mode": "strategy_first",
                "reason": "User requests strategy revision",
                "timestamp": datetime.now().isoformat(),
                "preserve_artifacts": False,
                "strategy_instructions": strategy_instructions,
            }

        # Default to full generation for unknown intent
        return {
            "intent": "full_generation",
            "mode": "complete",
            "reason": "Cannot determine specific intent - defaulting to full generation",
            "timestamp": datetime.now().isoformat(),
            "preserve_artifacts": False,
        }

    def _extract_text_instructions(self, user_intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract text regeneration instructions from user intent.

        Args:
            user_intent: User intent dictionary

        Returns:
            Dict containing text regeneration instructions or None
        """
        if not user_intent:
            return None

        # Check for specific text-focused instructions
        if user_intent.get("copy_modifications"):
            return {
                "type": "copy_modification",
                "modifications": user_intent["copy_modifications"],
                "platforms": user_intent.get("platforms", []),
            }

        if user_intent.get("headline_changes") or user_intent.get("body_modifications"):
            return {
                "type": "text_content_modification",
                "headline_changes": user_intent.get("headline_changes"),
                "body_modifications": user_intent.get("body_modifications"),
                "platforms": user_intent.get("platforms", []),
            }

        if user_intent.get("tone_adjustments") or user_intent.get("length_modifications"):
            return {
                "type": "style_modification",
                "tone_adjustments": user_intent.get("tone_adjustments"),
                "length_modifications": user_intent.get("length_modifications"),
                "platforms": user_intent.get("platforms", []),
            }

        return None

    def _extract_image_instructions(self, user_intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract image regeneration instructions from user intent.

        Args:
            user_intent: User intent dictionary

        Returns:
            Dict containing image regeneration instructions or None
        """
        if not user_intent:
            return None

        # Check for specific image-focused instructions
        if user_intent.get("visual_style_changes"):
            return {
                "type": "visual_style_modification",
                "visual_style_changes": user_intent["visual_style_changes"],
                "platforms": user_intent.get("platforms", []),
            }

        if user_intent.get("color_palette_changes") or user_intent.get("composition_changes"):
            return {
                "type": "aesthetic_modification",
                "color_palette_changes": user_intent.get("color_palette_changes"),
                "composition_changes": user_intent.get("composition_changes"),
                "platforms": user_intent.get("platforms", []),
            }

        if user_intent.get("brand_elements_modifications"):
            return {
                "type": "brand_elements_modification",
                "brand_elements_modifications": user_intent["brand_elements_modifications"],
                "platforms": user_intent.get("platforms", []),
            }

        return None

    def _extract_strategy_instructions(
        self, user_intent: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract strategy revision instructions from user intent.

        Args:
            user_intent: User intent dictionary

        Returns:
            Dict containing strategy revision instructions or None
        """
        if not user_intent:
            return None

        # Check for strategy-focused instructions
        if user_intent.get("campaign_goals_revisions") or user_intent.get("audience_changes"):
            return {
                "type": "strategy_revision",
                "campaign_goals_revisions": user_intent.get("campaign_goals_revisions"),
                "audience_changes": user_intent.get("audience_changes"),
                "platforms": user_intent.get("platforms", []),
            }

        if user_intent.get("voice_tone_changes") or user_intent.get("positioning_modifications"):
            return {
                "type": "messaging_revision",
                "voice_tone_changes": user_intent.get("voice_tone_changes"),
                "positioning_modifications": user_intent.get("positioning_modifications"),
                "platforms": user_intent.get("platforms", []),
            }

        return None

    def validate_intent_analysis(
        self, intent_result: Dict[str, Any], generation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate intent analysis results.

        Args:
            intent_result: Intent analysis result to validate
            generation_context: Complete generation context for validation

        Returns:
            Dict containing validation results and recommendations
        """
        errors = []
        warnings = []
        compliance_scores = {}

        intent = intent_result.get("intent")
        if not intent:
            errors.append(
                ValidationError(
                    code="MISSING_INTENT",
                    message="Intent analysis result missing intent",
                    severity=SeverityLevel.ERROR,
                    field="intent_analysis.intent",
                )
            )

        mode = intent_result.get("mode")
        if not mode:
            errors.append(
                ValidationError(
                    code="MISSING_MODE",
                    message="Intent analysis result missing generation mode",
                    severity=SeverityLevel.ERROR,
                    field="intent_analysis.mode",
                )
            )

        # Validate mode consistency with available artifacts
        if intent == "text_regeneration":
            if not generation_context.get("strategy"):
                warnings.append(
                    ValidationWarning(
                        code="MISSING_STRATEGY_FOR_TEXT_REGEN",
                        message="Text regeneration requested but no strategy available",
                        field="generation_context.strategy",
                    )
                )

        elif intent == "image_regeneration":
            if not generation_context.get("copy"):
                warnings.append(
                    ValidationWarning(
                        code="MISSING_COPY_FOR_IMAGE_REGEN",
                        message="Image regeneration requested but no copy available",
                        field="generation_context.copy",
                    )
                )

        # Validate preserve_artifacts configuration
        preserve_artifacts = intent_result.get("preserve_artifacts")
        if isinstance(preserve_artifacts, dict):
            for artifact, should_preserve in preserve_artifacts.items():
                if should_preserve and artifact not in generation_context:
                    warnings.append(
                        ValidationWarning(
                            code="PRESERVE_UNAVAIL_ARTIFACT",
                            message=f"Intent requests to preserve {artifact} but it is not available in generation context",
                            field="preserve_artifacts",
                        )
                    )

        # Calculate compliance scores
        required_checks = 3
        passed_checks = 0

        if intent:
            passed_checks += 1
        if mode:
            passed_checks += 1
        if isinstance(preserve_artifacts, dict) and len(preserve_artifacts) > 0:
            passed_checks += 1

        compliance_scores["analysis_completeness"] = (
            passed_checks / required_checks if required_checks > 0 else 0
        )

        is_valid = len(errors) == 0

        return {
            "id": f"validation_intent_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "intent_analysis",
            "artifact_id": "intent_validation",
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Ensure intent analysis includes all required fields",
                "Validate that preserve_artifacts configuration matches available artifacts",
                "Check that regeneration mode matches user instructions",
            ],
            "validated_by": "IntentAnalyzerService",
        }
