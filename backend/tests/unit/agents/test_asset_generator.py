"""Tests for the AssetGenerationAgent (Cloudflare image generation).

CloudflareImageService is mocked per constitution §Test-First. Because the
agent drives an async service via asyncio.run, the injected mock exposes an
async context manager and async generate methods.
"""

from unittest.mock import AsyncMock, MagicMock

from src.agents.asset_generator import AssetGenerationAgent
from src.agents.context import (
    BrandData,
    ContentDraft,
    EventData,
    GenerationContext,
)
from src.services.cloudflare_image_service import CloudflareImageServiceError


def _make_image_bytes() -> bytes:
    """Create minimal valid PNG bytes for testing."""
    # Minimal 1x1 PNG
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
        b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _service(img2img_bytes: bytes | None = None, text2img_bytes: bytes | None = None) -> MagicMock:
    service = MagicMock()
    service.img2img_model = "@cf/runwayml/stable-diffusion-v1-5-img2img"
    service.text2img_model = "@cf/black-forest-labs/flux-1-schnell"

    img_bytes = img2img_bytes or _make_image_bytes()
    txt_bytes = text2img_bytes or _make_image_bytes()

    service.generate_from_reference = AsyncMock(return_value=img_bytes)
    service.generate_from_text = AsyncMock(return_value=txt_bytes)
    service.download_reference = AsyncMock(return_value=b"fake_ref_bytes")

    # Mock async context manager
    service.__aenter__ = AsyncMock(return_value=service)
    service.__aexit__ = AsyncMock(return_value=None)

    return service


def _context(reference_urls=(), drafts=None) -> GenerationContext:
    brand = BrandData(
        company_name="Acme Corp",
        brand_tone="Confident",
        style_guide="clean minimal",
        reference_image_urls=tuple(reference_urls),
    )
    event = EventData(event_name="AI Summit")
    if drafts is None:
        drafts = (ContentDraft(slot_id="s1", image_prompt="event banner"),)
    return GenerationContext(brand=brand, event=event, content_drafts=drafts)


class TestGeneration:
    def test_attaches_image_url_and_model(self) -> None:
        service = _service()
        agent = AssetGenerationAgent(cloudflare_service=service)

        result = agent.execute(_context())

        assert result.success is True
        draft = result.context.content_drafts[0]
        assert draft.image_url.startswith("data:image/png;base64,")
        # No reference images → uses text2img
        assert draft.image_model == "@cf/black-forest-labs/flux-1-schnell"

    def test_reference_images_trigger_img2img(self) -> None:
        service = _service()
        agent = AssetGenerationAgent(cloudflare_service=service)

        agent.execute(_context(reference_urls=["https://ref/1.png"]))

        service.download_reference.assert_called_once_with("https://ref/1.png")
        service.generate_from_reference.assert_called_once()

    def test_prompt_includes_brand_style(self) -> None:
        service = _service()
        agent = AssetGenerationAgent(cloudflare_service=service)

        # With reference images → uses generate_from_reference
        agent.execute(_context(reference_urls=["https://ref/1.png"]))

        call_args = service.generate_from_reference.call_args
        prompt = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
        assert "event banner" in prompt
        assert "clean minimal" in prompt
        assert "Confident style" in prompt

    def test_generates_for_every_draft(self) -> None:
        service = _service()
        agent = AssetGenerationAgent(cloudflare_service=service)
        drafts = (
            ContentDraft(slot_id="s1", image_prompt="banner one"),
            ContentDraft(slot_id="s2", image_prompt="banner two"),
        )

        # With reference images → uses generate_from_reference
        result = agent.execute(_context(reference_urls=["https://ref/1.png"], drafts=drafts))

        assert service.generate_from_reference.await_count == 2
        assert all(d.image_url for d in result.context.content_drafts)

    def test_text2img_fallback_when_no_reference(self) -> None:
        service = _service()
        agent = AssetGenerationAgent(cloudflare_service=service)

        agent.execute(_context(reference_urls=()))

        service.generate_from_text.assert_called_once()
        service.generate_from_reference.assert_not_called()


class TestFailureHandling:
    def test_single_failure_does_not_abort_batch(self) -> None:
        service = MagicMock()
        service.img2img_model = "@cf/runwayml/stable-diffusion-v1-5-img2img"
        service.text2img_model = "@cf/black-forest-labs/flux-1-schnell"
        # No reference images → uses generate_from_text
        service.generate_from_text = AsyncMock(
            side_effect=[
                CloudflareImageServiceError("boom"),
                _make_image_bytes(),
            ]
        )
        service.download_reference = AsyncMock(return_value=None)
        service.__aenter__ = AsyncMock(return_value=service)
        service.__aexit__ = AsyncMock(return_value=None)

        agent = AssetGenerationAgent(cloudflare_service=service)
        drafts = (
            ContentDraft(slot_id="s1", image_prompt="a"),
            ContentDraft(slot_id="s2", image_prompt="b"),
        )

        result = agent.execute(_context(drafts=drafts))

        assert result.success is True
        out = result.context.content_drafts
        assert out[0].image_url == ""  # failed, degraded
        assert out[1].image_url.startswith("data:image/png;base64,")

    def test_no_drafts_fails(self) -> None:
        agent = AssetGenerationAgent(cloudflare_service=_service())
        ctx = GenerationContext(brand=BrandData(company_name="Acme"))

        result = agent.execute(ctx)

        assert result.success is False
