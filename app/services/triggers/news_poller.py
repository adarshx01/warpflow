import asyncio
import logging
import feedparser
import urllib.parse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.models import Workflow
from app.services.execution.engine import start_workflow
from app.services.triggers.news_utils import strip_html, resolve_url

logger = logging.getLogger(__name__)

_poller_task = None
_should_poll = False
POLL_INTERVAL_SECONDS = 60 * 15  # Poll every 15 minutes

# Track seen article URLs per workflow to avoid re-triggering
_seen_articles_cache = {}


async def _poll_news_for_workflows():
    """
    Background loop that polls Google News RSS for active workflows with a news-trigger node.
    Resolves real article URLs and strips HTML from snippets before triggering.
    """
    logger.info("📰 News Poller started...")
    while _should_poll:
        try:
            async with async_session() as db:
                stmt = select(Workflow).where(Workflow.is_active == True)
                result = await db.execute(stmt)
                workflows = result.scalars().all()

                for wf in workflows:
                    nodes = wf.nodes or []
                    news_trigger = next(
                        (node for node in nodes if node.get("type") == "news-trigger"), None
                    )

                    if not news_trigger:
                        continue

                    config = news_trigger.get("data", {})
                    query = config.get("query", "").strip()
                    language = config.get("language", "en").strip()

                    if not query:
                        continue

                    logger.debug("Checking news for Workflow %s | query: '%s'", wf.id, query)

                    if wf.id not in _seen_articles_cache:
                        _seen_articles_cache[wf.id] = set()

                    encoded_query = urllib.parse.quote_plus(query)
                    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={language}"

                    feed = await asyncio.to_thread(feedparser.parse, rss_url)

                    # Find new (unseen) entries
                    new_entries = []
                    for entry in feed.entries:
                        raw_url = getattr(entry, "link", "")
                        if raw_url and raw_url not in _seen_articles_cache[wf.id]:
                            new_entries.append(entry)
                            _seen_articles_cache[wf.id].add(raw_url)

                    # Trim cache to prevent unbounded growth
                    if len(_seen_articles_cache[wf.id]) > 200:
                        _seen_articles_cache[wf.id] = set(
                            list(_seen_articles_cache[wf.id])[-100:]
                        )

                    if not new_entries:
                        continue

                    # Resolve redirect URLs concurrently for all new entries
                    raw_urls = [getattr(e, "link", "") for e in new_entries]
                    real_urls = await asyncio.gather(*[resolve_url(u) for u in raw_urls])

                    # Trigger workflow for each new article
                    for entry, real_url in zip(new_entries, real_urls):
                        title = strip_html(getattr(entry, "title", ""))
                        snippet = strip_html(getattr(entry, "summary", ""))
                        source = (
                            getattr(entry, "source", {}).get("title", "Google News")
                            if hasattr(entry, "source") else "Google News"
                        )

                        logger.info(
                            "🔔 Triggering Workflow %s | article: %s", wf.id, title
                        )
                        trigger_data = {
                            "source": "news",
                            "payload": {
                                "title": title,
                                "url": real_url,
                                "snippet": snippet,
                                "source": source,
                                "published": getattr(entry, "published", ""),
                            },
                        }
                        await start_workflow(db, wf.id, trigger_data=trigger_data)

        except Exception as e:
            logger.error("Error in news poller: %s", e, exc_info=True)

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


def start_news_poller():
    global _poller_task, _should_poll
    if not _should_poll:
        _should_poll = True
        _poller_task = asyncio.create_task(_poll_news_for_workflows())
        logger.info("News Poller scheduled.")


async def stop_news_poller():
    global _poller_task, _should_poll
    _should_poll = False
    if _poller_task:
        _poller_task.cancel()
        try:
            await _poller_task
        except asyncio.CancelledError:
            pass
        logger.info("News Poller stopped.")
