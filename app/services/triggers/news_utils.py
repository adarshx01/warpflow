"""
Shared helpers for the Google News RSS integration.
"""
import re
import asyncio
import httpx


def strip_html(text: str) -> str:
    """Remove HTML tags and decode common HTML entities from a string."""
    if not text:
        return ""
    # Remove tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Decode common entities
    clean = (
        clean.replace("&amp;", "&")
             .replace("&lt;", "<")
             .replace("&gt;", ">")
             .replace("&quot;", '"')
             .replace("&#39;", "'")
             .replace("&nbsp;", " ")
    )
    # Collapse whitespace
    return re.sub(r"\s+", " ", clean).strip()


async def resolve_url(redirect_url: str, timeout: float = 8.0) -> str:
    """
    Follow a Google News RSS redirect to get the real article URL.
    Falls back to the original URL on any error.
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; WarpFlow/1.0)"},
        ) as client:
            resp = await client.head(redirect_url)
            final = str(resp.url)
            # If the redirect landed back on Google News, return original
            if "news.google.com" in final:
                return redirect_url
            return final
    except Exception:
        return redirect_url
