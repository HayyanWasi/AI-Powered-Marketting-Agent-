import pytest

from src.models.brand_style import BrandStyleContextInternal
from src.models.campaign_image import CampaignContext, CompanyProfile
from src.services.brand_style_service import BrandStyleService


@pytest.fixture
def service() -> BrandStyleService:
    return BrandStyleService()


@pytest.fixture
def full_profile() -> CompanyProfile:
    return CompanyProfile(
        id="test-id",
        name="Test Corp",
        brand_colors=["#FF6B35", "#004E89"],
        brand_personality="modern minimalist",
        style_guide="Clean lines, ample whitespace",
        logo_url="https://example.com/logo.png",
        typography_style="sans-serif",
        reference_images=["https://example.com/ref1.jpg", "https://example.com/ref2.jpg"],
        industry_category="technology",
    )


@pytest.fixture
def partial_profile() -> CompanyProfile:
    return CompanyProfile(
        id="test-id",
        name="Partial Corp",
        brand_colors=["#FF0000"],
        brand_personality=None,
        style_guide=None,
        logo_url=None,
        reference_images=None,
    )


@pytest.fixture
def empty_profile() -> CompanyProfile:
    return CompanyProfile(id="test-id", name="Empty Corp")


class TestExtractBrandContext:
    def test_full_brand_data(
        self, service: BrandStyleService, full_profile: CompanyProfile
    ) -> None:
        context = service.extract_brand_context(full_profile)
        assert context.color_palette == "#FF6B35, #004E89"
        assert context.personality_descriptors == "modern minimalist"
        assert context.style_guidance == "Clean lines, ample whitespace"
        assert context.logo_reference == "logo style from https://example.com/logo.png"
        assert context.reference_image_urls == [
            "https://example.com/ref1.jpg",
            "https://example.com/ref2.jpg",
        ]

    def test_partial_brand_data(
        self, service: BrandStyleService, partial_profile: CompanyProfile
    ) -> None:
        context = service.extract_brand_context(partial_profile)
        assert context.color_palette == "#FF0000"
        assert context.personality_descriptors is None
        assert context.style_guidance is None
        assert context.logo_reference is None
        assert context.reference_image_urls == []

    def test_empty_brand_data(
        self, service: BrandStyleService, empty_profile: CompanyProfile
    ) -> None:
        context = service.extract_brand_context(empty_profile)
        assert context.color_palette is None
        assert context.personality_descriptors is None
        assert context.style_guidance is None
        assert context.logo_reference is None
        assert context.reference_image_urls == []


class TestBuildPrompt:
    def test_includes_colors(self, service: BrandStyleService) -> None:
        context = BrandStyleContextInternal(color_palette="#FF6B35, #004E89")
        result = service.build_prompt("Summer sale", context)
        assert "brand colors #FF6B35, #004E89" in result.base_prompt
        assert result.model == "kontext"

    def test_includes_personality(self, service: BrandStyleService) -> None:
        context = BrandStyleContextInternal(personality_descriptors="modern minimalist")
        result = service.build_prompt("Product launch", context)
        assert "modern minimalist style" in result.base_prompt

    def test_includes_style_guide(self, service: BrandStyleService) -> None:
        context = BrandStyleContextInternal(style_guidance="Clean lines, whitespace")
        result = service.build_prompt("Event promo", context)
        assert "Clean lines, whitespace" in result.base_prompt

    def test_includes_logo_reference(self, service: BrandStyleService) -> None:
        context = BrandStyleContextInternal(
            logo_reference="logo style from https://example.com/logo.png"
        )
        result = service.build_prompt("Brand awareness", context)
        assert "logo reference logo style from" in result.base_prompt

    def test_includes_reference_images(self, service: BrandStyleService) -> None:
        context = BrandStyleContextInternal(
            reference_image_urls=["https://example.com/ref1.jpg", "https://example.com/ref2.jpg"]
        )
        result = service.build_prompt("Campaign", context)
        assert "reference image 1: https://example.com/ref1.jpg" in result.base_prompt
        assert "reference image 2: https://example.com/ref2.jpg" in result.base_prompt

    def test_includes_campaign_context(self, service: BrandStyleService) -> None:
        context = BrandStyleContextInternal()
        campaign_ctx = CampaignContext(
            platform="instagram",
            campaign_type="seasonal_sale",
            target_audience="young professionals",
        )
        result = service.build_prompt("Summer sale", context, campaign_ctx)
        assert "optimized for instagram" in result.base_prompt
        assert "seasonal_sale campaign" in result.base_prompt
        assert "targeting young professionals" in result.base_prompt

    def test_no_brand_data_uses_prompt_only(self, service: BrandStyleService) -> None:
        context = BrandStyleContextInternal()
        result = service.build_prompt("Just the prompt", context)
        assert result.base_prompt == "Just the prompt"

    def test_negative_prompt_included(self, service: BrandStyleService) -> None:
        context = BrandStyleContextInternal()
        result = service.build_prompt("Test", context)
        assert result.negative_prompt is not None
        assert "watermark" in result.negative_prompt

    def test_full_brand_and_context_combined(self, service: BrandStyleService) -> None:
        context = BrandStyleContextInternal(
            color_palette="#FF0000",
            personality_descriptors="bold",
            style_guidance="vibrant",
        )
        campaign_ctx = CampaignContext(platform="linkedin")
        result = service.build_prompt("Launch product", context, campaign_ctx)
        assert "brand colors #FF0000" in result.base_prompt
        assert "bold style" in result.base_prompt
        assert "vibrant" in result.base_prompt
        assert "optimized for linkedin" in result.base_prompt


class TestBuildFallbackPrompt:
    def test_with_brand_data(self, service: BrandStyleService) -> None:
        context = BrandStyleContextInternal(
            color_palette="#FF6B35", personality_descriptors="modern"
        )
        result = service.build_fallback_prompt(context)
        assert "brand colors #FF6B35" in result.base_prompt
        assert "modern style" in result.base_prompt
        assert result.model == "kontext"

    def test_without_brand_data(self, service: BrandStyleService) -> None:
        context = BrandStyleContextInternal()
        result = service.build_fallback_prompt(context)
        assert "placeholder" in result.base_prompt.lower()
        assert result.model == "kontext"
