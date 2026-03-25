import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, get_db, async_session
from app.models import Workflow
from app.services.execution.engine import start_workflow
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Note: In a production cluster, you'd want a Redis or DB-backed job store 
# so multiple workers don't execute the same schedule. 
# For now, we use a simple memory store, but this is the integration point.
scheduler = AsyncIOScheduler()

async def trigger_scheduled_workflow(workflow_id: str):
    """
    Called by APScheduler when a cron fires.
    """
    logger.info(f"⏰ Schedule fired for workflow: {workflow_id}")
    
    # We need a new DB session since this runs in the background
    async with async_session() as db:
        stmt = select(Workflow).where(Workflow.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()
        
        if not workflow or not workflow.is_active:
            logger.warning(f"Workflow {workflow_id} is not active or missing. Removing schedule.")
            remove_schedule(workflow_id)
            return
            
        await start_workflow(db, workflow.id, trigger_data={"source": "schedule", "payload": {}})

import re

def add_schedule(workflow_id: str, cron_expr: str):
    """
    Parse cron expression and add to APScheduler.
    cron_expr format: "minute hour day month day_of_week"
    """
    # Strict validation to prevent invalid cron strings from breaking APScheduler component
    cron_regex = re.compile(r'^(\*|([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])|\*\/([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])) (\*|([0-9]|1[0-9]|2[0-3])|\*\/([0-9]|1[0-9]|2[0-3])) (\*|([1-9]|1[0-9]|2[0-9]|3[0-1])|\*\/([1-9]|1[0-9]|2[0-9]|3[0-1])) (\*|([1-9]|1[0-2])|\*\/([1-9]|1[0-2])) (\*|([0-6])|\*\/([0-6]))$')
    
    if not cron_regex.match(cron_expr):
        logger.error(f"Invalid cron expression format for workflow {workflow_id}: {cron_expr}")
        return

    parts = cron_expr.split()
    if len(parts) != 5:
        logger.error(f"Invalid cron expression parts for workflow {workflow_id}: {cron_expr}")
        return
        
    try:
        # Remove existing if any
        remove_schedule(workflow_id)
        
        # Add new job
        scheduler.add_job(
            trigger_scheduled_workflow,
            trigger='cron',
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            id=str(workflow_id),
            args=[workflow_id],
            replace_existing=True
        )
        logger.info(f"Added schedule for workflow {workflow_id}: {cron_expr}")
    except Exception as e:
        logger.error(f"Failed to add schedule for {workflow_id}: {e}")

def remove_schedule(workflow_id: str):
    """Remove a workflow's schedule if it exists."""
    job_id = str(workflow_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Removed schedule for workflow {workflow_id}")

async def init_schedules():
    """Run on startup. Load all active workflows with schedule nodes."""
    logger.info("Initializing schedules...")
    async with async_session() as db:
        stmt = select(Workflow).where(Workflow.is_active == True)
        result = await db.execute(stmt)
        workflows = result.scalars().all()
        
        count = 0
        for wf in workflows:
            nodes = wf.nodes or []
            schedule_nodes = [n for n in nodes if n.get("type") == "schedule"]
            
            for node in schedule_nodes:
                data = node.get("data", {})
                cron = data.get("cron")
                if cron:
                    add_schedule(wf.id, cron)
                    count += 1
                    
        logger.info(f"Loaded {count} active schedules.")

def start_scheduler():
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()
