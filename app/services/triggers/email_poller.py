import asyncio
import logging
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.models import Workflow
from app.services.execution.engine import start_workflow

logger = logging.getLogger(__name__)

_poller_task = None
_should_poll = False
POLL_INTERVAL_SECONDS = 60 * 5  # Poll every 5 minutes

# In a fully fleshed out version, this would be a DB table for resilience
# Tracking seen message IDs ensures we don't double loop.
_processed_email_ids = set()

async def _poll_emails_for_workflows():
    """
    Background loop that polls Gmail for active workflows with an email-trigger node.
    """
    logger.info("📧 Email Poller started...")
    while _should_poll:
        try:
            async with async_session() as db:
                # Find all active workflows that contain an email-trigger
                stmt = select(Workflow).where(Workflow.is_active == True)
                result = await db.execute(stmt)
                workflows = result.scalars().all()
                
                for wf in workflows:
                    nodes = wf.nodes or []
                    email_trigger = next((node for node in nodes if node.get("type") == "email-trigger"), None)
                    
                    if email_trigger:
                        config = email_trigger.get("data", {})
                        body_regex_str = config.get("bodyMatch", "")
                        
                        logger.debug(f"Checking emails for Workflow: {wf.id}")
                        # TODO: Fetch user's Gmail credentials and query IMAP for unread emails.
                        # For each unread email fetched:
                        # 1. if email.id in _processed_email_ids: continue
                        # 2. _processed_email_ids.add(email.id)
                        # 3. body = email.get_plain_text()
                        # 4. if body_regex_str:
                        #        if not re.search(body_regex_str, body, re.IGNORECASE):
                        #            continue # Regex didn't match, skip workflow trigger
                        # 5. await start_workflow(db, wf.id, trigger_data={"source": "email", "payload": {"subject": email.subject, "body": body}})
                        
                        pass
                        
        except Exception as e:
            logger.error(f"Error in email poller: {e}")
            
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

def start_email_poller():
    global _poller_task, _should_poll
    if not _should_poll:
        _should_poll = True
        _poller_task = asyncio.create_task(_poll_emails_for_workflows())
        logger.info("Email Poller scheduled to run.")

async def stop_email_poller():
    global _poller_task, _should_poll
    _should_poll = False
    if _poller_task:
        _poller_task.cancel()
        try:
            await _poller_task
        except asyncio.CancelledError:
            pass
        logger.info("Email Poller stopped.")
