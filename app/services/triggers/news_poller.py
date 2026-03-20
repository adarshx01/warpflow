import asyncio
import logging
import feedparser
import urllib.parse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.models import Workflow
from app.services.execution.engine import start_workflow

logger = logging.getLogger(__name__)

_poller_task = None
_should_poll = False
POLL_INTERVAL_SECONDS = 60 * 15  # Poll every 15 minutes by default

# Track seen article URLs per workflow to avoid re-triggering
_seen_articles_cache = {}

async def _poll_news_for_workflows():
    """
    Background loop that polls Google News RSS for active workflows with a news-trigger node.
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
                    news_trigger = next((node for node in nodes if node.get("type") == "news-trigger"), None)
                    
                    if news_trigger:
                        config = news_trigger.get("data", {})
                        query = config.get("query", "").strip()
                        language = config.get("language", "en").strip()
                        
                        if not query:
                            continue
                            
                        logger.debug(f"Checking news for Workflow: {wf.id} with query '{query}'")
                        
                        # Initialize cache for this workflow if not exists
                        if wf.id not in _seen_articles_cache:
                            _seen_articles_cache[wf.id] = set()

                        # Construct Google News RSS URL
                        encoded_query = urllib.parse.quote_plus(query)
                        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={language}"
                        
                        feed = await asyncio.to_thread(feedparser.parse, rss_url)
                        
                        new_articles = []
                        for entry in feed.entries:
                            url = getattr(entry, "link", "")
                            if url and url not in _seen_articles_cache[wf.id]:
                                new_articles.append(entry)
                                _seen_articles_cache[wf.id].add(url)
                                
                                if len(_seen_articles_cache[wf.id]) > 100:
                                    _seen_articles_cache[wf.id] = set(list(_seen_articles_cache[wf.id])[-50:])
                        
                        # Trigger workflow for each new article found
                        for article in new_articles:
                            logger.info(f"Triggering Workflow {wf.id} for new article: {article.title}")
                            trigger_data = {
                                "source": "news",
                                "payload": {
                                    "title": getattr(article, "title", ""),
                                    "url": getattr(article, "link", ""),
                                    "snippet": getattr(article, "description", ""),
                                    "published": getattr(article, "published", "")
                                }
                            }
                            await start_workflow(db, wf.id, trigger_data=trigger_data)
                            
        except Exception as e:
            logger.error(f"Error in news poller: {e}", exc_info=True)
            
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

def start_news_poller():
    global _poller_task, _should_poll
    if not _should_poll:
        _should_poll = True
        _poller_task = asyncio.create_task(_poll_news_for_workflows())
        logger.info("News Poller scheduled to run.")

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
