"""Central configuration, sourced entirely from environment variables.

No secret has a hardcoded default. The only required variable is OPENAI_API_KEY;
everything else has a safe, cost-bounded default that can be overridden per deploy.
This is a shared superset across the 14-agents challenge — some fields are unused
by a given agent, which is harmless.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Load a local .env for development if python-dotenv is installed. In production
# (Cloud Run) real env vars / secrets are set directly; existing env vars always win.
try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except ImportError:
    pass


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _csv(name: str, default: str) -> list[str]:
    return [x.strip() for x in os.environ.get(name, default).split(",") if x.strip()]


@dataclass(frozen=True)
class Config:
    # Models
    model: str = os.environ.get("OPENAI_MODEL", "gpt-5.6")
    embed_model: str = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    reasoning_effort: str = os.environ.get("OPENAI_REASONING_EFFORT", "medium")
    max_output_tokens: int = _int("OPENAI_MAX_OUTPUT_TOKENS", 4000)

    # Web search (server tool)
    web_search_tool: str = os.environ.get("OPENAI_WEB_SEARCH_TOOL", "web_search")
    max_pause_restarts: int = _int("MAX_PAUSE_RESTARTS", 6)

    # RAG / upload params (used by document-style agents)
    chunk_size: int = _int("CHUNK_SIZE", 1200)
    chunk_overlap: int = _int("CHUNK_OVERLAP", 150)
    top_k: int = _int("TOP_K", 4)
    embed_batch: int = _int("EMBED_BATCH", 64)
    max_file_mb: int = _int("MAX_FILE_MB", 5)
    max_doc_chars: int = _int("MAX_DOC_CHARS", 200_000)
    max_chunks: int = _int("MAX_CHUNKS", 400)

    # Input / abuse / cost guards
    max_input_chars: int = _int("MAX_INPUT_CHARS", 12_000)
    min_input_chars: int = _int("MIN_INPUT_CHARS", 3)
    rate_limit_per_min: int = _int("RATE_LIMIT_PER_MIN", 8)
    daily_call_cap: int = _int("DAILY_CALL_CAP", 300)

    # Embedding (iframe) allow-list
    allowed_embed_origins: tuple = tuple(
        _csv(
            "ALLOWED_EMBED_ORIGINS",
            "https://amoldesai.in,https://www.amoldesai.in,https://amoldesai-portfolio.web.app",
        )
    )

    @property
    def api_key_present(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))


CONFIG = Config()
