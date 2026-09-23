import pytest
import json
from unittest.mock import MagicMock, patch

from src.agents.video_script_agent import VideoScriptAgent, VideoScene
from src.models.video_generation_context import VideoGenerationContext
from src.models.brand_context import BrandContext

@pytest.fixture
def dummy_context():
    return VideoGenerationContext(
        campaign_id="11111111-1111-1111-1111-111111111111",
        owner_id="22222222-2222-2222-2222-222222222222",
        plan_id="33333333-3333-3333-3333-333333333333",
        plan_version=1,
        campaign_name="Test Campaign",
        campaign_type="webinar",
        strategy="Some strategy",
        target_audience="Devs",
        research_status="completed",
        research_context="Some research",
        user_instruction="Make a video",
        brand=BrandContext(company_profile_id="12345678-1234-5678-1234-567812345678", company_name="Test Company", industry="Tech"),
        venue="Online",
        guest="Guest"
    )

def create_mock_llm_response(data: dict) -> MagicMock:
    response = MagicMock()
    response.text = json.dumps(data)
    return response

@pytest.mark.asyncio
async def test_valid_5_scenes(dummy_context):
    agent = VideoScriptAgent()
    valid_data = {
        "scenes": [
            {"scene_number": i, "narration": f"narration {i} Test Company", "image_prompt": f"prompt {i}"}
            for i in range(1, 6)
        ]
    }
    
    with patch("src.agents.video_script_agent.LLMService.generate", return_value=create_mock_llm_response(valid_data)):
        # Should not raise exception
        scenes = await agent.generate_script(dummy_context)
        assert len(scenes) == 5
        assert isinstance(scenes[0], VideoScene)

@pytest.mark.asyncio
async def test_4_scenes_fails(dummy_context):
    agent = VideoScriptAgent()
    invalid_data = {
        "scenes": [
            {"scene_number": i, "narration": f"narration {i}", "image_prompt": f"prompt {i}"}
            for i in range(1, 5)
        ]
    }
    
    with patch("src.agents.video_script_agent.LLMService.generate", return_value=create_mock_llm_response(invalid_data)):
        with pytest.raises(ValueError, match="exactly five scenes"):
            await agent.generate_script(dummy_context)

@pytest.mark.asyncio
async def test_6_scenes_fails(dummy_context):
    agent = VideoScriptAgent()
    invalid_data = {
        "scenes": [
            {"scene_number": i, "narration": f"narration {i}", "image_prompt": f"prompt {i}"}
            for i in range(1, 7)
        ]
    }
    
    with patch("src.agents.video_script_agent.LLMService.generate", return_value=create_mock_llm_response(invalid_data)):
        with pytest.raises(ValueError, match="exactly five scenes"):
            await agent.generate_script(dummy_context)

@pytest.mark.asyncio
async def test_missing_narration_fails(dummy_context):
    agent = VideoScriptAgent()
    invalid_data = {
        "scenes": [
            {"scene_number": i, "narration": f"narration {i}" if i != 3 else "   ", "image_prompt": f"prompt {i}"}
            for i in range(1, 6)
        ]
    }
    
    with patch("src.agents.video_script_agent.LLMService.generate", return_value=create_mock_llm_response(invalid_data)):
        with pytest.raises(ValueError, match="requires narration and an image prompt"):
            await agent.generate_script(dummy_context)

@pytest.mark.asyncio
async def test_invalid_scene_order_fails(dummy_context):
    agent = VideoScriptAgent()
    # Out of order
    invalid_data = {
        "scenes": [
            {"scene_number": i, "narration": f"narration {i}", "image_prompt": f"prompt {i}"}
            for i in [1, 2, 4, 3, 5]
        ]
    }
    
    with patch("src.agents.video_script_agent.LLMService.generate", return_value=create_mock_llm_response(invalid_data)):
        with pytest.raises(ValueError, match="ordered 1 through 5"):
            await agent.generate_script(dummy_context)
