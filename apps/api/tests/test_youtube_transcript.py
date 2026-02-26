"""Tests for YouTubeService.get_transcript (§4 — uses youtube-transcript-api)."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.youtube import YouTubeService

# The library is imported inside get_transcript(), so we patch the source module.
_PATCH_TARGET = "youtube_transcript_api.YouTubeTranscriptApi"


def _make_transcript(texts):
    return [{"text": t, "start": i * 5.0, "duration": 4.9} for i, t in enumerate(texts)]


@pytest.mark.asyncio
async def test_transcript_returns_joined_text():
    svc = YouTubeService()
    fake_parts = _make_transcript(["Hello world", "this is a test"])

    with patch(_PATCH_TARGET) as MockApi:
        MockApi.get_transcript.return_value = fake_parts
        result = await svc.get_transcript("dQw4w9WgXcQ")

    assert result == "Hello world this is a test"


@pytest.mark.asyncio
async def test_transcript_uses_english_language_preference():
    svc = YouTubeService()
    fake_parts = _make_transcript(["Only one line"])

    with patch(_PATCH_TARGET) as MockApi:
        MockApi.get_transcript.return_value = fake_parts
        await svc.get_transcript("dQw4w9WgXcQ")
        _, call_kwargs = MockApi.get_transcript.call_args
        assert "en" in call_kwargs["languages"]


@pytest.mark.asyncio
async def test_transcript_falls_back_on_no_transcript_found():
    """NoTranscriptFound → try list_transcripts fallback → returns None if both fail."""
    from youtube_transcript_api import NoTranscriptFound

    svc = YouTubeService()

    with patch(_PATCH_TARGET) as MockApi:
        MockApi.get_transcript.side_effect = NoTranscriptFound("vid", ["en"], MagicMock())
        MockApi.list_transcripts.side_effect = Exception("no transcripts at all")
        result = await svc.get_transcript("dQw4w9WgXcQ")

    assert result is None


@pytest.mark.asyncio
async def test_transcript_falls_back_on_transcripts_disabled():
    from youtube_transcript_api import TranscriptsDisabled

    svc = YouTubeService()

    with patch(_PATCH_TARGET) as MockApi:
        MockApi.get_transcript.side_effect = TranscriptsDisabled("dQw4w9WgXcQ")
        MockApi.list_transcripts.side_effect = Exception("disabled")
        result = await svc.get_transcript("dQw4w9WgXcQ")

    assert result is None


@pytest.mark.asyncio
async def test_transcript_fallback_list_transcripts_succeeds():
    """If primary get_transcript fails, list_transcripts path returns text."""
    from youtube_transcript_api import NoTranscriptFound

    svc = YouTubeService()
    fake_parts = _make_transcript(["Fallback text"])

    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = fake_parts

    mock_transcript_list = MagicMock()
    mock_transcript_list.find_transcript.return_value = mock_transcript

    with patch(_PATCH_TARGET) as MockApi:
        MockApi.get_transcript.side_effect = NoTranscriptFound("vid", ["en"], MagicMock())
        MockApi.list_transcripts.return_value = mock_transcript_list
        result = await svc.get_transcript("vid")

    assert result == "Fallback text"


@pytest.mark.asyncio
async def test_transcript_extracts_video_id_from_url():
    """Full YouTube URLs should resolve to the correct video ID."""
    svc = YouTubeService()
    fake_parts = _make_transcript(["URL test"])

    with patch(_PATCH_TARGET) as MockApi:
        MockApi.get_transcript.return_value = fake_parts
        await svc.get_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        video_id_used = MockApi.get_transcript.call_args[0][0]
        assert video_id_used == "dQw4w9WgXcQ"


@pytest.mark.asyncio
async def test_transcript_returns_none_on_unexpected_error():
    svc = YouTubeService()
    with patch(_PATCH_TARGET) as MockApi:
        MockApi.get_transcript.side_effect = RuntimeError("network blip")
        MockApi.list_transcripts.side_effect = RuntimeError("also broke")
        result = await svc.get_transcript("any-id")
    assert result is None
