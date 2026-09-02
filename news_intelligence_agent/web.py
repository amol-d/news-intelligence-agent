"""Shared web wiring: FastAPI mount, iframe-embedding CSP, health check, runner."""

from __future__ import annotations

import os

import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import CONFIG
from .security import RateLimiter

# One shared limiter per process.
LIMITER = RateLimiter()


def caller_id(request) -> str:
    """Best-effort per-caller id (Cloud Run puts the client IP first in XFF)."""
    if request is None:
        return "unknown"
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    client = getattr(request, "client", None)
    return getattr(client, "host", "unknown") if client else "unknown"


class FrameAncestorsMiddleware(BaseHTTPMiddleware):
    """Allow only configured origins to embed this app (CSP frame-ancestors)."""

    def __init__(self, app, origins):
        super().__init__(app)
        self._value = "frame-ancestors 'self' " + " ".join(origins)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = self._value
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if "X-Frame-Options" in response.headers:
            del response.headers["X-Frame-Options"]
        return response


def make_app(demo, title: str = "Agent") -> FastAPI:
    """Mount a Gradio Blocks app on FastAPI with security headers + health check."""
    app = FastAPI(title=title)
    app.add_middleware(FrameAncestorsMiddleware, origins=CONFIG.allowed_embed_origins)

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        return "ok" if CONFIG.api_key_present else "degraded: no api key"

    return gr.mount_gradio_app(app, demo, path="/")


def run(app) -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
