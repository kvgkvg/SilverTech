from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import admin_submissions, docs, query, stt, submissions, templates, vision, vision_logs
from app.services.env_loader import load_env_file
from app.services.logging_config import configure_logging
from app.storage.database import ROOT
from app.storage.database import initialize_database

load_env_file()
configure_logging()
initialize_database()

app = FastAPI(
    title="SilverTech MVP API",
    version="0.1.0",
    description="Template retrieval, Vietnamese guidance, and reviewed-template APIs.",
)

# Any localhost port stays allowed so `flutter run -d chrome`, which picks a
# random port, needs no configuration. Deployed frontends (Vercel) are named
# one per line in SILVERTECH_CORS_ORIGINS, comma separated. A wildcard is not
# an option here: allow_credentials=True forbids it.
_DEV_ORIGIN_REGEX = r"^http://(localhost|127\.0\.0\.1):\d+$"


def _configured_cors_origins() -> list[str]:
    raw = os.getenv("SILVERTECH_CORS_ORIGINS", "")
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_configured_cors_origins(),
    allow_origin_regex=_DEV_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vision.router)
app.include_router(templates.router)
app.include_router(stt.router)
app.include_router(query.router)
app.include_router(vision_logs.router)
app.include_router(submissions.router)
app.include_router(admin_submissions.router)
app.include_router(docs.router)
app.mount(
    "/data/templates",
    StaticFiles(directory=ROOT / "data" / "templates"),
    name="template-images",
)
# Both are written at runtime, so a fresh clone has neither; StaticFiles refuses
# to mount a directory that does not exist yet.
_tts_dir = ROOT / "data" / "tts"
_tts_dir.mkdir(parents=True, exist_ok=True)
app.mount("/data/tts", StaticFiles(directory=_tts_dir), name="tts-audio")

_submissions_dir = ROOT / "data" / "submissions"
_submissions_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/data/submissions",
    StaticFiles(directory=_submissions_dir),
    name="submission-images",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
