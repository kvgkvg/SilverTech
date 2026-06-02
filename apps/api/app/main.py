from __future__ import annotations

from fastapi import FastAPI

from app.api import admin_submissions, docs, query, stt, submissions, templates, vision, vision_logs
from app.services.logging_config import configure_logging
from app.storage.database import initialize_database

configure_logging()
initialize_database()

app = FastAPI(
    title="SilverTech MVP API",
    version="0.1.0",
    description="Template retrieval, Vietnamese guidance, and reviewed-template APIs.",
)

app.include_router(vision.router)
app.include_router(templates.router)
app.include_router(stt.router)
app.include_router(query.router)
app.include_router(vision_logs.router)
app.include_router(submissions.router)
app.include_router(admin_submissions.router)
app.include_router(docs.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
