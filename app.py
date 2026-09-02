"""Gradio demo UI for the News Intelligence Agent, mounted on FastAPI."""

from __future__ import annotations

import gradio as gr

from news_intelligence_agent.agent import NewsAgent
from news_intelligence_agent.config import CONFIG
from news_intelligence_agent.security import RateLimitError, ValidationError, sanitize_text
from news_intelligence_agent.web import LIMITER, caller_id, make_app, run

_agent: NewsAgent | None = None


def _get_agent() -> NewsAgent:
    global _agent
    if _agent is None:
        _agent = NewsAgent()
    return _agent


def handle(topic: str, request: gr.Request):
    try:
        clean = sanitize_text(topic, field="a topic", min_chars=2, max_chars=200)
    except ValidationError as exc:
        yield f"⚠️ {exc}", ""
        return
    try:
        LIMITER.check(caller_id(request))
    except RateLimitError as exc:
        yield f"⏳ {exc}", ""
        return
    if not CONFIG.api_key_present:
        yield "⚠️ The demo is not configured (missing API key). See the GitHub repo to run it locally.", ""
        return
    yield "📰 Searching and compiling the briefing…", ""
    try:
        result = _get_agent().brief(clean)
    except Exception:  # noqa: BLE001
        yield "⚠️ Something went wrong. Please try again in a moment.", ""
        return
    if not result.sources:
        yield result.text or "No briefing could be produced.", ""
        return
    lines = "\n".join(f"{i}. [{(s.title or s.url)}]({s.url})" for i, s in enumerate(result.sources, 1))
    yield result.text, f"**Sources**\n\n{lines}"


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="News Intelligence Agent — Day 06", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            "## 📰 News Intelligence Agent\n"
            "Enter a topic; get a de-duplicated, **cited** news briefing.\n\n"
            "*Day 06 of 14 AI Agents in 14 Days — search, dedupe, summarize.*"
        )
        topic = gr.Textbox(label="Topic", placeholder="e.g. AI regulation, or a company / event…", lines=1)
        run_btn = gr.Button("Compile briefing", variant="primary")
        out = gr.Markdown()
        sources = gr.Markdown()
        gr.Examples(examples=["Latest in open-source AI models", "Electric vehicle market trends"], inputs=topic)
        run_btn.click(handle, inputs=topic, outputs=[out, sources])
        topic.submit(handle, inputs=topic, outputs=[out, sources])
    demo.queue(default_concurrency_limit=2, max_size=20)
    return demo


app = make_app(build_demo(), title="News Intelligence Agent")

if __name__ == "__main__":
    run(app)
