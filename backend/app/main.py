"""
FastAPI application entrypoint: creates the app, wires up CORS, registers
every route module, creates app-DB tables on startup (no Alembic — this is a
student project, `create_all` is enough and one less moving part to explain),
and adds a couple of global exception handlers so unexpected errors still
come back as friendly JSON instead of a raw stack trace.
"""
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, chat, connections, export, pdf, saved_queries
from app.config import settings
from app.database import Base, engine
from app.models import *  # noqa: F401,F403 - ensures all models are registered on Base.metadata
from app.schema_sync import sync_columns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_sql_assistant")

app = FastAPI(
    title="AI SQL Assistant API",
    description="Natural language to SQL, over your own connected Postgres database.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(connections.router)
app.include_router(chat.router)
app.include_router(saved_queries.router)
app.include_router(pdf.router)
app.include_router(export.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    sync_columns(engine)  # create_all() adds tables but never new columns on existing ones
    logger.info("App database tables ensured.")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Keeps the error shape consistent (`{"detail": "..."}`) for the frontend."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our end. Please try again in a moment."},
    )
