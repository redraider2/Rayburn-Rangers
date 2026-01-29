import os
import httpx

YT_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


async def youtube_search(query: str, max_results: int = 12):
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing YOUTUBE_API_KEY")

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "date",
        "maxResults": max(1, min(max_results, 50)),
        "safeSearch": "none",
        "key": api_key,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(YT_SEARCH_URL, params=params)
        if r.status_code >= 400:
            print("YouTube API error status:", r.status_code)
            print("YouTube API error body:", r.text)
        r.raise_for_status()
        return r.json()
