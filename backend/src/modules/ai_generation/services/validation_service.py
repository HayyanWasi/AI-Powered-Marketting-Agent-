"""Validation service for AI Generation Engine."""

from typing import Any, Dict, List

from ..constants import SeverityLevel


class ValidationError:
    """Individual validation error."""

    def __init__(
        self, code: str, message: str, severity: str, field: str = None, suggested_fix: str = None
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

    def __init__(self, code: str, message: str, field: str = None):
        self.code = code
        self.message = message
        self.field = field

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
        }


class ValidationService:
    """Service for validating all generated artifacts against business rules."""

    def validate_all_artifacts(
        self,
        artifacts: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate all generated artifacts against business rules and platform requirements.

        Args:
            artifacts: Dictionary containing all artifacts to validate
                      (strategy, copy, image prompts, images)

        Returns:
            ValidationArtifact: Comprehensive validation results

        Raises:
            ValidationError: If validation fails or is malformed
        """
        strategy = artifacts.get("strategy")
        copy_artifacts = artifacts.get("copy", [])
        image_prompts = artifacts.get("image_prompts", [])
        images = artifacts.get("images", [])

        # Validate each artifact type
        strategy_results = self.validate_strategy(strategy) if strategy else None
        copy_results = self.validate_copies(copy_artifacts)
        prompt_results = self.validate_image_prompts(image_prompts)
        image_results = self.validate_images(images, image_prompts)

        # Combine results
        all_errors = []
        all_warnings = []
        compliance_scores = {}

        if strategy_results:
            all_errors.extend(strategy_results["errors"])
            all_warnings.extend(strategy_results["warnings"])
            compliance_scores.update(strategy_results["compliance_scores"])

        all_errors.extend(copy_results["errors"])
        all_warnings.extend(copy_results["warnings"])
        compliance_scores.update(copy_results["compliance_scores"])

        all_errors.extend(prompt_results["errors"])
        all_warnings.extend(prompt_results["warnings"])
        compliance_scores.update(prompt_results["compliance_scores"])

        all_errors.extend(image_results["errors"])
        all_warnings.extend(image_results["warnings"])
        compliance_scores.update(image_results["compliance_scores"])

        # Calculate overall validation results
        overall_is_valid = (
            (strategy_results["is_valid"] if strategy_results else True)
            and copy_results["is_valid"]
            and prompt_results["is_valid"]
            and image_results["is_valid"]
        )

        # Calculate overall compliance scores
        for key, value in copy_results["compliance_scores"].items():
            if key not in compliance_scores:
                compliance_scores[key] = value

        validation_result = {
            "id": f"validation_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "comprehensive",
            "artifact_id": "validation_results",
            "is_valid": overall_is_valid,
            "errors": all_errors,
            "warnings": all_warnings,
            "compliance_scores": compliance_scores,
            "recommendations": self._generate_recommendations(all_errors, all_warnings),
            "validated_by": "ValidationService",
        }

        return validation_result

    def validate_artifact(
        self,
        artifact: Dict[str, Any],
        artifact_type: str,
    ) -> Dict[str, Any]:
        """
        Validate a specific artifact type against appropriate rules.

        Args:
            artifact: Artifact to validate
            artifact_type: Type of artifact (strategy, copy, image_prompt, image)

        Returns:
            ValidationArtifact: Validation results
        """
        if artifact_type == "strategy":
            return self.validate_strategy(artifact)
        elif artifact_type == "copy":
            return self.validate_copy(artifact)
        elif artifact_type == "image_prompt":
            return self.validate_image_prompt(artifact)
        elif artifact_type == "image":
            return self.validate_image(artifact)
        else:
            raise ValueError(f"Unsupported artifact type: {artifact_type}")

    def validate_strategy(
        self,
        strategy: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate strategy artifact against business rules.

        Args:
            strategy: Strategy artifact to validate

        Returns:
            ValidationArtifact: Validation results
        """
        errors = []
        warnings = []
        compliance_scores = {}

        # Check required fields
        required_fields = [
            "id",
            "audience_strategy",
            "messaging_strategy",
            "platform_strategy",
            "campaign_strategy",
        ]

        for field in required_fields:
            if not strategy.get(field):
                errors.append(
                    ValidationError(
                        code="MISSING_STRATEGY_FIELD",
                        message=f"Missing required strategy field: {field}",
                        severity=SeverityLevel.ERROR,
                        field=f"strategy.{field}",
                    )
                )

        # Validate audience strategy
        audience_strategy = strategy.get("audience_strategy", {})
        if not audience_strategy.get("target_segments"):
            warnings.append(
                ValidationWarning(
                    code="MISSING_AUDIENCE_SEGMENTS",
                    message="Audience segments are recommended for targeting",
                    field="audience_strategy.target_segments",
                )
            )

        # Validate platform strategy
        platform_strategy = strategy.get("platform_strategy", {})
        if not platform_strategy.get("platforms"):
            warnings.append(
                ValidationWarning(
                    code="EMPTY_PLATFORMS",
                    message="No platforms specified in strategy",
                    field="platform_strategy.platforms",
                )
            )
        elif len(platform_strategy["platforms"]) > 10:
            warnings.append(
                ValidationWarning(
                    code="TOO_MANY_PLATFORMS",
                    message="Many platforms specified - strategy may be too dispersed",
                    field="platform_strategy.platforms",
                )
            )

        # Validate campaign strategy
        campaign_strategy = strategy.get("campaign_strategy", {})
        if not campaign_strategy.get("goals"):
            warnings.append(
                ValidationWarning(
                    code="EMPTY_CAMPAIGN_GOALS",
                    message="Campaign goals are empty - may lack direction",
                    field="campaign_strategy.goals",
                )
            )

        # Check internal consistency
        if campaign_strategy.get("goals") and audience_strategy.get("target_segments"):
            goals = campaign_strategy["goals"]
            segments = audience_strategy["target_segments"]
            if isinstance(goals, list) and len(goals) > 3:
                warnings.append(
                    ValidationWarning(
                        code="TOO_MANY_GOALS",
                        message="Too many campaign goals may dilute focus",
                        field="campaign_strategy.goals",
                    )
                )

        # Compliance scores
        present_fields = sum(1 for field in required_fields if strategy.get(field))
        compliance_scores["required_fields"] = (
            present_fields / len(required_fields) if required_fields else 0
        )

        is_valid = len(errors) == 0

        return {
            "id": f"validation_strategy_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "strategy",
            "artifact_id": strategy.get("id", "unknown"),
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Ensure all required strategy fields are populated",
                "Define specific audience segments for better targeting",
                "Set clear, achievable campaign goals",
                "Limit platform count to maintain focus",
            ],
            "validated_by": "ValidationService",
        }

    def validate_copies(
        self,
        copy_artifacts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Validate copy artifacts against platform requirements.

        Args:
            copy_artifacts: List of copy artifacts to validate

        Returns:
            ValidationArtifact: Validation results
        """
        all_errors = []
        all_warnings = []
        compliance_scores = {}
        total_copies = len(copy_artifacts)

        if total_copies == 0:
            return {
                "id": f"validation_copy_{datetime.now().isoformat()}",
                "generated_at": datetime.now().isoformat(),
                "artifact_type": "copy",
                "artifact_id": "validation_results",
                "is_valid": False,
                "errors": [
                    ValidationError(
                        code="NO_COPIES_GENERATED",
                        message="No copy artifacts were generated",
                        severity=SeverityLevel.ERROR,
                    ).to_dict()
                ],
                "warnings": [],
                "compliance_scores": {"total_copies": 0},
                "recommendations": ["Ensure copy generation was attempted"],
                "validated_by": "ValidationService",
            }

        # Validate each copy
        for i, copy in enumerate(copy_artifacts):
            copy_result = self.validate_copy(copy)
            all_errors.extend(copy_result["errors"])
            all_warnings.extend(copy_result["warnings"])
            # Adjust compliance scores for weighted average
            for key, value in copy_result["compliance_scores"].items():
                if key not in compliance_scores:
                    compliance_scores[key] = []
                compliance_scores[key].append(value)

        # Calculate weighted compliance scores
        for key, values in compliance_scores.items():
            if isinstance(values, list):
                compliance_scores[key] = sum(values) / len(values) if values else 0

        compliance_scores["total_copies"] = total_copies

        is_valid = len(all_errors) == 0

        return {
            "id": f"validation_copy_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "copy",
            "artifact_id": "validation_results",
            "is_valid": is_valid,
            "errors": all_errors,
            "warnings": all_warnings,
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Review copy for platform-specific requirements",
                "Check for keyword density and readability",
                "Validate character limits for each platform",
                "Ensure brand voice consistency",
            ],
            "validated_by": "ValidationService",
        }

    def validate_copy(
        self,
        copy: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate single copy artifact.

        Args:
            copy: Copy artifact to validate

        Returns:
            ValidationArtifact: Validation results
        """
        errors = []
        warnings = []
        compliance_scores = {}

        # Check required fields
        required_fields = [
            "id",
            "headlines",
            "captions",
            "ctas",
            "hashtags",
            "platform",
        ]

        for field in required_fields:
            if not copy.get(field):
                errors.append(
                    ValidationError(
                        code="MISSING_COPY_FIELD",
                        message=f"Missing required copy field: {field}",
                        severity=SeverityLevel.ERROR,
                        field=f"copy.{field}",
                    )
                )

        # Validate content quality
        headlines = copy.get("headlines", [])
        if len(headlines) == 0:
            warnings.append(
                ValidationWarning(
                    code="NO_HEADLINES",
                    message="No headlines provided - may reduce engagement",
                    field="headlines",
                )
            )
        elif len(headlines) > 5:
            warnings.append(
                ValidationWarning(
                    code="TOO_MANY_HEADLINES",
                    message="Too many headlines may dilute message",
                    field="headlines",
                )
            )

        captions = copy.get("captions", [])
        if len(captions) == 0:
            warnings.append(
                ValidationWarning(
                    code="NO_CAPTIONS",
                    message="No captions provided - may reduce narrative depth",
                    field="captions",
                )
            )

        # Validate platform-specific constraints
        platform = copy.get("platform")
        if platform:
            if platform == "twitter":
                # Twitter has character limits
                total_chars = (
                    sum(len(h) for h in headlines)
                    + sum(len(c) for c in captions)
                    + sum(len(t) for t in copy.get("ctas", []))
                )
                if total_chars > 280:
                    warnings.append(
                        ValidationWarning(
                            code="TWITTER_CHAR_LIMIT",
                            message=f"Total content may exceed Twitter's 280-character limit",
                            field="content_length",
                        )
                    )
            elif platform == "linkedin":
                # LinkedIn requires professional tone
                if not any(any(c.isalpha() and c.islower() for c in h.lower()) for h in headlines):
                    warnings.append(
                        ValidationWarning(
                            code="LINKEDIN_PROFESSIONAL_TONE",
                            message="LinkedIn content may lack professional tone",
                            field="headlines",
                        )
                    )
            elif platform == "instagram":
                # Instagram works well with visual elements
                if not copy.get("hashtags"):
                    warnings.append(
                        ValidationWarning(
                            code="INSTAGRAM_HASHTAGS",
                            message="Instagram content may benefit from hashtags",
                            field="hashtags",
                        )
                    )

        # Compliance scores
        present_fields = sum(1 for field in required_fields if copy.get(field))
        compliance_scores["required_fields"] = (
            present_fields / len(required_fields) if required_fields else 0
        )

        is_valid = len(errors) == 0

        return {
            "id": f"validation_copy_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "copy",
            "artifact_id": copy.get("id", "unknown"),
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Ensure required fields are populated",
                "Validate platform-specific constraints",
                "Check character limits for social media",
                "Maintain brand voice consistency",
            ],
            "validated_by": "ValidationService",
        }

    def validate_image_prompts(
        self,
        image_prompts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Validate image prompt artifacts.

        Args:
            image_prompts: List of image prompt artifacts to validate

        Returns:
            ValidationArtifact: Validation results
        """
        all_errors = []
        all_warnings = []
        compliance_scores = {}

        if len(image_prompts) == 0:
            return {
                "id": f"validation_image_prompt_{datetime.now().isoformat()}",
                "generated_at": datetime.now().isoformat(),
                "artifact_type": "image_prompt",
                "artifact_id": "validation_results",
                "is_valid": False,
                "errors": [
                    ValidationError(
                        code="NO_IMAGE_PROMPTS",
                        message="No image prompts were generated",
                        severity=SeverityLevel.ERROR,
                    ).to_dict()
                ],
                "warnings": [],
                "compliance_scores": {"total_prompts": 0},
                "recommendations": ["Ensure image prompt generation was attempted"],
                "validated_by": "ValidationService",
            }

        # Validate each prompt
        for i, prompt in enumerate(image_prompts):
            prompt_result = self.validate_image_prompt(prompt)
            all_errors.extend(prompt_result["errors"])
            all_warnings.extend(prompt_result["warnings"])

        # Calculate overall results
        is_valid = len(all_errors) == 0

        return {
            "id": f"validation_image_prompt_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "image_prompt",
            "artifact_id": "validation_results",
            "is_valid": is_valid,
            "errors": all_errors,
            "warnings": all_warnings,
            "compliance_scores": {"total_prompts": len(image_prompts)},
            "recommendations": [
                "Ensure prompts are descriptive and brand-aligned",
                "Validate strategy and copy consistency",
                "Check platform-specific requirements",
            ],
            "validated_by": "ValidationService",
        }

    def validate_image_prompt(
        self,
        prompt: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate single image prompt artifact.

        Args:
            prompt: Image prompt artifact to validate

        Returns:
            ValidationArtifact: Validation results
        """
        errors = []
        warnings = []
        compliance_scores = {}

        # Check required fields
        required_fields = [
            "id",
            "strategy_id",
            "copy_id",
            "platform",
            "prompt_text",
            "style_guidelines",
            "brand_elements",
            "visual_elements",
            "composition_guidelines",
        ]

        for field in required_fields:
            if not prompt.get(field):
                errors.append(
                    ValidationError(
                        code="MISSING_PROMPT_FIELD",
                        message=f"Missing required prompt field: {field}",
                        severity=SeverityLevel.ERROR,
                        field=f"prompt.{field}",
                    )
                )

        # Validate prompt content
        prompt_text = prompt.get("prompt_text", "")
        if len(prompt_text) < 20:
            warnings.append(
                ValidationWarning(
                    code="SHORT_PROMPT",
                    message="Prompt text is too short for effective image generation",
                    field="prompt_text",
                )
            )

        if not any(word in prompt_text.lower() for word in ["image", "picture", "visual"]):
            warnings.append(
                ValidationWarning(
                    code="NO_IMAGE_KEYWORD",
                    message="Prompt does not clearly indicate image generation",
                    field="prompt_text",
                )
            )

        # Validate brand elements
        brand_elements = prompt.get("brand_elements", [])
        if not brand_elements:
            warnings.append(
                ValidationWarning(
                    code="NO_BRAND_ELEMENTS",
                    message="Prompt contains no brand elements",
                    field="brand_elements",
                )
            )

        # Validate visual elements
        visual_elements = prompt.get("visual_elements", [])
        if not visual_elements:
            warnings.append(
                ValidationWarning(
                    code="NO_VISUAL_ELEMENTS",
                    message="Prompt contains no visual concepts",
                    field="visual_elements",
                )
            )

        # Validate consistency with strategy
        strategy_id = prompt.get("strategy_id")
        copy_id = prompt.get("copy_id")
        if strategy_id and not strategy_id.isdigit():
            warnings.append(
                ValidationWarning(
                    code="STRATEGY_ID_FORMAT",
                    message="Strategy ID format may be invalid",
                    field="strategy_id",
                )
            )

        if copy_id and not copy_id.isdigit():
            warnings.append(
                ValidationWarning(
                    code="COPY_ID_FORMAT",
                    message="Copy ID format may be invalid",
                    field="copy_id",
                )
            )

        # Compliance scores
        present_fields = sum(1 for field in required_fields if prompt.get(field))
        compliance_scores["required_fields"] = (
            present_fields / len(required_fields) if required_fields else 0
        )

        is_valid = len(errors) == 0

        return {
            "id": f"validation_image_prompt_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "image_prompt",
            "artifact_id": prompt.get("id", "unknown"),
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Ensure all required fields are populated",
                "Include clear visual concepts and descriptions",
                "Add brand elements for alignment",
                "Validate prompt consistency with strategy",
            ],
            "validated_by": "ValidationService",
        }

    def validate_images(
        self,
        images: List[Dict[str, Any]],
        image_prompts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Validate generated images against prompts and guidelines.

        Args:
            images: List of generated images to validate
            image_prompts: List of corresponding image prompts for validation

        Returns:
            ValidationArtifact: Validation results
        """
        all_errors = []
        all_warnings = []
        compliance_scores = {}

        if len(images) == 0:
            return {
                "id": f"validation_image_{datetime.now().isoformat()}",
                "generated_at": datetime.now().isoformat(),
                "artifact_type": "image",
                "artifact_id": "validation_results",
                "is_valid": False,
                "errors": [
                    ValidationError(
                        code="NO_IMAGES_GENERATED",
                        message="No images were generated",
                        severity=SeverityLevel.ERROR,
                    ).to_dict()
                ],
                "warnings": [],
                "compliance_scores": {"total_images": 0},
                "recommendations": ["Ensure image generation was attempted"],
                "validated_by": "ValidationService",
            }

        # Validate each image
        for i, image in enumerate(images):
            # Find corresponding prompt
            prompt = None
            for prompt_candidate in image_prompts:
                if prompt_candidate.get("id") == image.get("prompt_id"):
                    prompt = prompt_candidate
                    break

            if not prompt:
                # If no matching prompt found, create minimal validation
                image_result = self.validate_image(image)
                all_errors.extend(image_result["errors"])
                all_warnings.extend(image_result["warnings"])
            else:
                # Full validation with prompt
                image_result = self.validate_image(image, prompt)
                all_errors.extend(image_result["errors"])
                all_warnings.extend(image_result["warnings"])

        # Calculate overall results
        is_valid = len(all_errors) == 0

        # Calculate compliance scores
        if images:
            brand_score_total = 0
            platform_score_total = 0
            valid_images = 0

            for image in images:
                brand_score = image.get("brand_alignment", {}).get("overall_score", 0)
                platform_score = image.get("platform_suitability", {}).get("overall_score", 0)
                if brand_score > 0:
                    brand_score_total += brand_score
                if platform_score > 0:
                    platform_score_total += platform_score
                if brand_score > 0.5 and platform_score > 0.5:
                    valid_images += 1

            compliance_scores = {
                "total_images": len(images),
                "brand_alignment": round(brand_score_total / len(images), 2) if images else 0,
                "platform_suitability": (
                    round(platform_score_total / len(images), 2) if images else 0
                ),
                "valid_images_percentage": (
                    round((valid_images / len(images)) * 100, 2) if images else 0
                ),
            }
        else:
            compliance_scores = {"total_images": 0}

        return {
            "id": f"validation_image_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "image",
            "artifact_id": "validation_results",
            "is_valid": is_valid,
            "errors": all_errors,
            "warnings": all_warnings,
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Ensure brand alignment and platform suitability",
                "Validate image quality and resolution",
                "Check prompt consistency",
                "Review accessibility features",
            ],
            "validated_by": "ValidationService",
        }

    def validate_image(
        self,
        image: Dict[str, Any],
        prompt: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Validate single image artifact.

        Args:
            image: Image artifact to validate
            prompt: Corresponding image prompt for validation (optional)

        Returns:
            ValidationArtifact: Validation results
        """
        errors = []
        warnings = []
        compliance_scores = {}

        # Check required fields
        required_fields = [
            "id",
            "generated_at",
            "prompt_id",
            "platform",
            "image_url",
            "metadata",
            "brand_alignment",
            "platform_suitability",
        ]

        for field in required_fields:
            if not image.get(field):
                errors.append(
                    ValidationError(
                        code="MISSING_IMAGE_FIELD",
                        message=f"Missing required image field: {field}",
                        severity=SeverityLevel.ERROR,
                        field=f"image.{field}",
                    )
                )

        # Validate with corresponding prompt if provided
        if prompt:
            if image.get("prompt_id") != prompt.get("id"):
                errors.append(
                    ValidationError(
                        code="PROMPT_ID_MISMATCH",
                        message="Image prompt ID does not match source prompt",
                        severity=SeverityLevel.ERROR,
                        field="image.prompt_id",
                    )
                )

            # Validate platform consistency
            strategy_platforms = prompt.get("strategy_data", {}).get("platforms", [])
            image_platform = image.get("platform")
            if strategy_platforms and image_platform and image_platform not in strategy_platforms:
                warnings.append(
                    ValidationWarning(
                        code="PLATFORM_NOT_IN_STRATEGY",
                        message=f"Image platform '{image_platform}' not in strategy platforms",
                        field="image.platform",
                    )
                )

        # Validate image metadata
        metadata = image.get("metadata", {})
        if metadata.get("width", 0) <= 0 or metadata.get("height", 0) <= 0:
            errors.append(
                ValidationError(
                    code="INVALID_DIMENSIONS",
                    message="Invalid image dimensions",
                    severity=SeverityLevel.ERROR,
                    field="metadata.dimensions",
                )
            )

        if not metadata.get("format"):
            warnings.append(
                ValidationWarning(
                    code="MISSING_FORMAT",
                    message="Image format not specified",
                    field="metadata.format",
                )
            )

        if metadata.get("size_bytes", 0) <= 0:
            warnings.append(
                ValidationWarning(
                    code="INVALID_SIZE",
                    message="Invalid image size",
                    field="metadata.size_bytes",
                )
            )

        # Validate brand alignment
        brand_alignment = image.get("brand_alignment", {})
        if brand_alignment.get("overall_score", 0) < 0.5:
            warnings.append(
                ValidationWarning(
                    code="LOW_BRAND_ALIGNMENT",
                    message="Brand alignment score is low",
                    field="brand_alignment.overall_score",
                )
            )

        if brand_alignment.get("overall_score", 0) < 0.3:
            errors.append(
                ValidationError(
                    code="POOR_BRAND_ALIGNMENT",
                    message="Brand alignment is critically poor",
                    severity=SeverityLevel.ERROR,
                    field="brand_alignment.overall_score",
                )
            )

        # Validate platform suitability
        platform_suitability = image.get("platform_suitability", {})
        if platform_suitability.get("overall_score", 0) < 0.5:
            warnings.append(
                ValidationWarning(
                    code="LOW_PLATFORM_SUITABILITY",
                    message="Platform suitability score is low",
                    field="platform_suitability.overall_score",
                )
            )

        if platform_suitability.get("overall_score", 0) < 0.3:
            errors.append(
                ValidationError(
                    code="POOR_PLATFORM_SUITABILITY",
                    message="Platform suitability is critically poor",
                    severity=SeverityLevel.ERROR,
                    field="platform_suitability.overall_score",
                )
            )

        # Compliance scores
        present_fields = sum(1 for field in required_fields if image.get(field))
        compliance_scores["required_fields"] = (
            present_fields / len(required_fields) if required_fields else 0
        )

        if brand_alignment:
            compliance_scores["brand_alignment"] = brand_alignment.get("overall_score", 0)
        if platform_suitability:
            compliance_scores["platform_suitability"] = platform_suitability.get("overall_score", 0)

        is_valid = len(errors) == 0

        return {
            "id": f"validation_image_{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat(),
            "artifact_type": "image",
            "artifact_id": image.get("id", "unknown"),
            "is_valid": is_valid,
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "compliance_scores": compliance_scores,
            "recommendations": [
                "Ensure all required fields are populated",
                "Match prompt and image IDs consistently",
                "Validate brand alignment and platform suitability",
                "Check image dimensions and format",
            ],
            "validated_by": "ValidationService",
        }

    def _generate_recommendations(
        self,
        errors: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate recommendations based on validation errors and warnings."""
        recommendations = []

        # Analyze errors
        error_codes = [e["code"] for e in errors]
        if "MISSING_STRATEGY_FIELD" in error_codes:
            recommendations.append("Ensure all required strategy fields are populated")
        if "MISSING_COPY_FIELD" in error_codes:
            recommendations.append("Populate all required copy fields")
        if "MISSING_PROMPT_FIELD" in error_codes:
            recommendations.append("Ensure all required prompt fields are set")
        if "MISSING_IMAGE_FIELD" in error_codes:
            recommendations.append("Ensure all required image fields are populated")

        # Analyze warnings
        warning_codes = [w["code"] for w in warnings]
        if "EMPTY_PLATFORMS" in warning_codes:
            recommendations.append("Define target platforms for campaign")
        if "EMPTY_CAMPAIGN_GOALS" in warning_codes:
            recommendations.append("Set clear campaign goals and objectives")
        if "TOO_MANY_PLATFORMS" in warning_codes:
            recommendations.append("Limit platforms to maintain focus")
        if "SHORT_PROMPT" in warning_codes:
            recommendations.append("Expand prompt descriptions for better image generation")
        if "NO_BRAND_ELEMENTS" in warning_codes:
            recommendations.append("Add brand elements to prompts and images")
        if "NO_VISUAL_ELEMENTS" in warning_codes:
            recommendations.append("Include visual concepts in prompts")
        if "LOW_BRAND_ALIGNMENT" in warning_codes:
            recommendations.append("Improve brand element placement and consistency")
        if "LOW_PLATFORM_SUITABILITY" in warning_codes:
            recommendations.append("Review platform-specific requirements")

        if not recommendations:
            recommendations = [
                "Review and complete missing required fields",
                "Validate artifact consistency across pipeline",
                "Check platform and brand guidelines compliance",
            ]

        return recommendations
