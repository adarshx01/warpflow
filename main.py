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

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed node templates
    await _seed_node_templates()

    yield
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


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
