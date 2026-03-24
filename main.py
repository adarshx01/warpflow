import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import engine, Base, async_session
from app.rate_limit import limiter
from app.auth.router import router as auth_router
from app.workflows.router import router as workflows_router, templates_router
from app.services.google.google_docs.router import router as google_docs_router
from app.services.credentials_router import router as credentials_router
from app.services.google.google_drive.router import router as google_drive_router
from app.services.google.gmail.router import router as gmail_router
from app.services.google.google_sheets.router import router as google_sheets_router
from app.services.google.google_forms.router import router as google_forms_router
from app.services.ai.openai_service.router import router as openai_router
from app.services.ai.gemini_service.router import router as gemini_router
from app.services.agent.router import router as agent_router
from app.services.secrets_router import router as secrets_router
from app.services.ml.router import router as ml_router
from app.services.context.router import router as context_router
from app.services.cv_router.router import router as cv_router
from app.services.twilio.router import router as twilio_router
from app.services.elevenlabs.router import router as elevenlabs_router
from app.services.postgresql.router import router as postgresql_router
from app.services.call_conversation.router import router as call_conversation_router
from app.workflows.execution import router as execution_router
from app.webhooks.router import router as webhooks_router
from app.services.scheduler import init_schedules, start_scheduler, stop_scheduler
from app.services.triggers.email_poller import start_email_poller, stop_email_poller
from app.services.triggers.news_poller import start_news_poller, stop_news_poller
from app.services.triggers.news_router import router as news_router

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed node templates
    await _seed_node_templates()

    # Start scheduler and trigger pollers
    start_scheduler()
    await init_schedules()
    start_email_poller()
    start_news_poller()

    yield

    await stop_news_poller()
    await stop_email_poller()
    stop_scheduler()
    await engine.dispose()


async def _seed_node_templates():
    """Insert default node templates if the table is empty."""
    from sqlalchemy import select as sa_select
    from app.models import NodeTemplate
    from app.workflows.seed import NODE_TEMPLATES

    async with async_session() as db:
        result = await db.execute(sa_select(NodeTemplate).limit(1))
        if result.first() is not None:
            return  # already seeded

        for tmpl in NODE_TEMPLATES:
            db.add(NodeTemplate(**tmpl))
        await db.commit()
        logger.info("Seeded %d node templates", len(NODE_TEMPLATES))


app = FastAPI(
    title="WarpCore API",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow frontend origin with specific methods and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all so even 500s pass through CORSMiddleware with proper headers."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Routers
app.include_router(auth_router)
app.include_router(workflows_router)
app.include_router(templates_router)
app.include_router(credentials_router)
app.include_router(google_docs_router)
app.include_router(google_drive_router)
app.include_router(gmail_router)
app.include_router(google_sheets_router)
app.include_router(google_forms_router)
app.include_router(openai_router)
app.include_router(gemini_router)
app.include_router(agent_router)
app.include_router(secrets_router)
app.include_router(ml_router)
app.include_router(context_router)
app.include_router(cv_router)
app.include_router(twilio_router)
app.include_router(elevenlabs_router)
app.include_router(postgresql_router)
app.include_router(call_conversation_router)
app.include_router(execution_router)
app.include_router(webhooks_router)
app.include_router(news_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
