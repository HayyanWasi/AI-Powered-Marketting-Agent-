import pytest

from src.services.video_generation_service import VideoGenerationService


@pytest.fixture
def service():
    # Bypass remote supabase connection in unit tests
    service = VideoGenerationService.__new__(VideoGenerationService)
    service.bucket = "campaign_assets"
    return service


def test_align_words_with_text(service):
    original = "Imagine saving tax without effort. New fintech app cuts tax burden."
    stream_words = [
        {"offset": 1000000, "duration": 5000000, "text": "Imagine"},
        {"offset": 6000000, "duration": 3000000, "text": "saving"},
        {"offset": 9000000, "duration": 3000000, "text": "tax"},
        {"offset": 12000000, "duration": 2000000, "text": "without"},
        {"offset": 14000000, "duration": 4000000, "text": "effort"},
        {"offset": 24000000, "duration": 2000000, "text": "New"},
        {"offset": 26000000, "duration": 3000000, "text": "fintech"},
        {"offset": 29000000, "duration": 1000000, "text": "app"},
        {"offset": 30000000, "duration": 2000000, "text": "cuts"},
        {"offset": 32000000, "duration": 2000000, "text": "tax"},
        {"offset": 34000000, "duration": 4000000, "text": "burden"},
    ]

    aligned = service._align_words_with_text(stream_words, original)
    assert len(aligned) == len(stream_words)
    # Check that punctuation was restored
    assert aligned[4]["word"] == "effort."
    assert aligned[10]["word"] == "burden."
    # Check timestamps
    assert aligned[0]["start"] == pytest.approx(0.1)
    assert aligned[0]["end"] == pytest.approx(0.6)


def test_chunk_words_for_subtitles(service):
    words = [
        {"word": "Imagine", "start": 0.1, "end": 0.6, "duration": 0.5},
        {"word": "saving", "start": 0.63, "end": 0.97, "duration": 0.34},
        {"word": "tax", "start": 0.98, "end": 1.33, "duration": 0.35},
        {"word": "without", "start": 1.35, "end": 1.63, "duration": 0.28},
        {"word": "effort.", "start": 1.64, "end": 2.08, "duration": 0.44},
        {"word": "New", "start": 2.41, "end": 2.67, "duration": 0.26},
        {"word": "fintech", "start": 2.68, "end": 3.03, "duration": 0.35},
        {"word": "app", "start": 3.06, "end": 3.19, "duration": 0.13},
        {"word": "cuts", "start": 3.20, "end": 3.48, "duration": 0.28},
        {"word": "tax", "start": 3.49, "end": 3.75, "duration": 0.26},
        {"word": "burden.", "start": 3.76, "end": 4.23, "duration": 0.47},
    ]

    chunks = service._chunk_words_for_subtitles(words, max_words=5)
    assert len(chunks) >= 2

    for ch in chunks:
        # Maximum 2 lines
        lines = ch["text"].split("\n")
        assert len(lines) <= 2
        # Max words per chunk constraint
        assert ch["words_count"] <= 6
        # Positive duration
        assert ch["end"] > ch["start"]

    # Strict non-overlapping enforcement:
    for i in range(len(chunks) - 1):
        assert chunks[i]["end"] <= chunks[i + 1]["start"]


def test_create_text_clip_pil(service):
    text = "Imagine saving tax\nwithout effort."
    clip = service._create_text_clip_pil(text)
    assert clip is not None
    # Check dimensions
    w, h = clip.size
    assert 100 < w <= 720
    assert 30 < h <= 200


def test_fallback_chunker(service, tmp_path):
    full_text = "Imagine saving tax without effort New fintech app cuts tax burden Launch event showcases game changing savings Hands on demos experts explain strategy Free event 500 seats register below"
    # Even with dummy audio path, fallback chunker returns valid short chunks
    chunks = service._chunk_from_cues_or_text([], full_text, tmp_path / "dummy.mp3")
    assert len(chunks) > 1
    for ch in chunks:
        lines = ch["text"].split("\n")
        assert len(lines) <= 2
        assert ch["words_count"] <= 6
