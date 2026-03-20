import asyncio
import feedparser
import urllib.parse
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/preview")
async def preview_news(q: str = Query(..., description="Search query"), lang: str = Query("en")):
    """
    Fetch real news articles from Google News RSS, sorted newest → oldest.
    Used by the frontend to test the News Trigger configuration.
    """
    encoded_query = urllib.parse.quote_plus(q)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang}"

    feed = await asyncio.to_thread(feedparser.parse, rss_url)

    articles = []
    for entry in feed.entries:
        articles.append({
            "title": getattr(entry, "title", "No title"),
            "url": getattr(entry, "link", ""),
            "source": getattr(entry, "source", {}).get("title", "Google News") if hasattr(entry, "source") else "Google News",
            "published": getattr(entry, "published", ""),
            "_ts": entry.get("published_parsed"),  # time.struct_time or None
        })

    # Sort newest first; articles with no date sink to the bottom
    articles.sort(key=lambda a: a["_ts"] or (0,) * 9, reverse=True)

    # Strip the internal sort key before returning
    for a in articles:
        del a["_ts"]

    return JSONResponse({"query": q, "articles": articles[:5]})
