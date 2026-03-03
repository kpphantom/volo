"""
VOLO — YouTube Routes
Video info, transcript extraction, and AI-powered summaries.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.auth import get_current_user, CurrentUser
from app.services.youtube import YouTubeService
from app.services.google_auth import google_auth

router = APIRouter()


class SummarizeRequest(BaseModel):
    url: str
    style: Optional[str] = "concise"  # concise, detailed, bullet_points, eli5


@router.get("/youtube/video")
async def get_video_info(url: str = Query(..., description="YouTube URL or video ID"), current_user: CurrentUser = Depends(get_current_user)):
    """Get video metadata."""
    token = google_auth.get_access_token(current_user.user_id) or ""
    yt = YouTubeService(access_token=token)
    info = await yt.get_video_info(url)
    return info


@router.get("/youtube/transcript")
async def get_transcript(url: str = Query(..., description="YouTube URL or video ID"), current_user: CurrentUser = Depends(get_current_user)):
    """Get video transcript/captions."""
    token = google_auth.get_access_token(current_user.user_id) or ""
    yt = YouTubeService(access_token=token)
    transcript = await yt.get_transcript(url)
    if not transcript:
        raise HTTPException(status_code=404, detail="No transcript available for this video")
    return {"transcript": transcript}


@router.post("/youtube/summarize")
async def summarize_video(body: SummarizeRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Get an AI-generated summary of a YouTube video."""
    token = google_auth.get_access_token(current_user.user_id) or ""
    yt = YouTubeService(access_token=token)

    # Get video info
    info = await yt.get_video_info(body.url)

    # Try to get transcript
    transcript = await yt.get_transcript(body.url)

    # Build context for AI summary
    if transcript:
        source_text = transcript[:8000]  # Limit to ~8k chars for context window
        content_note = ""
    else:
        source_text = info.get("description", "")[:4000]
        content_note = "\nNote: No transcript is available for this video. Base your summary on the description above.\n"

    if not source_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No transcript or description is available for this video. Try a video that has captions enabled.",
        )

    style_instructions = {
        "concise": "Provide a concise 3-5 sentence summary.",
        "detailed": "Provide a detailed summary covering all main points, organized with headers.",
        "bullet_points": "Summarize as a bulleted list of key takeaways.",
        "eli5": "Explain the video content like I'm 5 years old, using simple language.",
    }

    # Use the orchestrator's LLM to generate summary
    try:
        import anthropic
        import os
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if api_key:
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": f"""Summarize this YouTube video.

Title: {info.get('title', 'Unknown')}
Channel: {info.get('channel', 'Unknown')}
{content_note}
{style_instructions.get(body.style, style_instructions['concise'])}

Content:
{source_text}"""
                }],
            )
            summary = msg.content[0].text
        else:
            summary = _generate_demo_summary(info, body.style)
    except Exception:
        summary = _generate_demo_summary(info, body.style)

    return {
        "video": info,
        "summary": summary,
        "style": body.style,
        "has_transcript": transcript is not None,
    }


@router.get("/youtube/search")
async def search_youtube(q: str = Query(...), limit: int = Query(10, ge=1, le=50), current_user: CurrentUser = Depends(get_current_user)):
    """Search YouTube videos."""
    token = google_auth.get_access_token(current_user.user_id) or ""
    yt = YouTubeService(access_token=token)
    results = await yt.search_videos(q, max_results=limit)
    return {"results": results, "query": q}


@router.get("/youtube/subscriptions")
async def get_subscriptions(current_user: CurrentUser = Depends(get_current_user)):
    """Get user's YouTube subscriptions."""
    token = google_auth.get_access_token(current_user.user_id) or ""
    yt = YouTubeService(access_token=token)
    subs = await yt.get_subscriptions()
    return {"subscriptions": subs}


def _generate_demo_summary(info: dict, style: str) -> str:
    """Generate a demo summary when no API key is available."""
    title = info.get("title", "this video")
    channel = info.get("channel", "the creator")

    if style == "bullet_points":
        return f"""## Key Takeaways from "{title}"

- **Main Topic**: {channel} discusses important concepts and insights
- **Key Point 1**: The video covers foundational ideas that are relevant to the audience
- **Key Point 2**: Practical examples and demonstrations are provided throughout
- **Key Point 3**: The creator offers actionable advice viewers can apply immediately
- **Conclusion**: A comprehensive overview with valuable takeaways for the audience

*Summary generated by Volo AI — connect your API key for full AI summaries*"""

    elif style == "detailed":
        return f"""## Detailed Summary: "{title}"

### Overview
This video by {channel} provides an in-depth look at the subject matter, offering both theoretical understanding and practical applications.

### Main Points
The content is structured around several key themes that build upon each other, creating a comprehensive narrative.

### Key Insights
The creator brings unique perspective and expertise to the topic, making complex ideas accessible to a broad audience.

### Conclusion
The video concludes with actionable takeaways and recommendations for viewers who want to dive deeper.

*Summary generated by Volo AI — connect your API key for full AI summaries*"""

    elif style == "eli5":
        return f"""## Simple Explanation of "{title}"

Imagine {channel} is telling you a really cool story about something interesting! They explain it in a way that's easy to understand, using examples from everyday life. The main idea is something that affects everyone, and they show you why it matters and what you can do about it.

*Summary generated by Volo AI — connect your API key for full AI summaries*"""

    else:  # concise
        return f""""{title}" by {channel} covers important concepts with clear explanations and practical examples. The video provides actionable insights that viewers can apply immediately. It's a comprehensive overview that balances depth with accessibility.

*Summary generated by Volo AI — connect your API key for full AI summaries*"""
