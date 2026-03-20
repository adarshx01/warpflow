import asyncio
import feedparser
import urllib.parse
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from app.services.triggers.news_utils import strip_html, resolve_url

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/preview")
async def preview_news(q: str = Query(..., description="Search query"), lang: str = Query("en")):
    """
    Fetch real news articles from Google News RSS, sorted newest → oldest.
    Resolves actual article URLs and strips HTML from snippets.
    """
    encoded_query = urllib.parse.quote_plus(q)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang}"

    feed = await asyncio.to_thread(feedparser.parse, rss_url)

    # Resolve all redirect URLs concurrently
    entries = feed.entries
    redirect_urls = [getattr(e, "link", "") for e in entries]
    real_urls = await asyncio.gather(*[resolve_url(u) for u in redirect_urls])

    articles = []
    for entry, real_url in zip(entries, real_urls):
        articles.append({
            "title": strip_html(getattr(entry, "title", "No title")),
            "url": real_url,
            "source": getattr(entry, "source", {}).get("title", "Google News") if hasattr(entry, "source") else "Google News",
            "published": getattr(entry, "published", ""),
            "snippet": strip_html(getattr(entry, "summary", "")),
            "_ts": entry.get("published_parsed"),
        })

    # Sort newest first
    articles.sort(key=lambda a: a["_ts"] or (0,) * 9, reverse=True)
    for a in articles:
        del a["_ts"]

    return JSONResponse({"query": q, "articles": articles[:5]})
