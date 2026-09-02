# Security

This is a public demo that feeds untrusted user input to an LLM and spends the
owner's API budget. The design addresses each risk explicitly.

- **Secret exposure:** the OpenAI key is read from the environment by the SDK —
  never committed (`.env` git-ignored; `.env.example` only), logged, rendered, or
  sent to the browser; excluded from the image (`.dockerignore`). In production,
  store it in **Google Secret Manager** and inject with `--set-secrets`.
- **Prompt injection:** all user- and tool-provided content is treated as untrusted
  **data**, not instructions — the agent's system prompt refuses embedded commands
  (task-switching, "ignore previous", system-prompt extraction).
- **Cost abuse / denial-of-wallet:** a per-caller **rate limit** (`RATE_LIMIT_PER_MIN`,
  keyed by `X-Forwarded-For`) plus a **global daily cap** (`DAILY_CALL_CAP`); output
  bounded by `OPENAI_MAX_OUTPUT_TOKENS` and `OPENAI_REASONING_EFFORT`; concurrency by
  the Gradio queue. Set a GCP billing budget alert as a backstop. The in-memory
  limiter is per-instance — for multi-instance Cloud Run keep `--max-instances 1` or
  use a shared store.
- **Input validation:** length-bounded and control-char-stripped (hygiene, not an
  injection filter).
- **Clickjacking / embedding:** CSP `frame-ancestors` restricts framing to
  `ALLOWED_EMBED_ORIGINS`; `X-Frame-Options` is intentionally not `DENY`.
- **Error handling & supply chain:** exceptions are caught and replaced with generic
  messages — no internals/credentials reach the UI. Dependencies are version-pinned;
  the container runs as a **non-root** user.

## Reporting

Open a GitHub issue (no sensitive details) or contact the owner via the portfolio.
