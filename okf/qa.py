"""
Answer generation: take retrieved OKF concepts, assemble grounded context,
stream a response from a local Ollama model, citing concepts by title/path.
"""
from __future__ import annotations

from .retrieval import RetrievedConcept

SYSTEM_PROMPT = """\
You are an enterprise knowledge assistant. You answer questions using ONLY \
the knowledge concepts provided below, which come from the organization's Open Knowledge Format \
(OKF) bundle. Each concept includes its type, title, and source document.

Rules:
- Answer only from the provided concepts. If they don't contain the answer, say so plainly.
- Every claim must be followed by a citation in the form [Title](path).
- If concepts conflict, point out the conflict rather than picking one silently.
- Be concise and direct."""


def _format_context(results: list[RetrievedConcept], bundle_root) -> str:
    blocks = []
    for r in results:
        relpath = str(r.concept.path.relative_to(bundle_root)) if r.concept.path else "unknown"
        blocks.append(
            f"### {r.concept.title}\n"
            f"- type: {r.concept.type}\n"
            f"- source document: {r.concept.resource}\n"
            f"- path: {relpath}\n\n"
            f"{r.concept.body}\n"
        )
    return "\n---\n".join(blocks)


def stream_answer_question(
    question: str,
    results: list[RetrievedConcept],
    bundle_root,
    history: list[dict[str, str]] = None,
    model: str = "llama3",
    host: str = "http://localhost:11434",
):
    """Stream an answer from a local Ollama model, yielding text chunks."""
    if not results:
        yield (
            "I couldn't find any relevant concepts in the knowledge bundle for that question. "
            "Try rephrasing, or ingest more documents first."
        )
        return

    import json
    import requests

    api_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    # Append chat history for multi-turn capability
    if history:
        for msg in history:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    context = _format_context(results, bundle_root)
    api_messages.append({
        "role": "user",
        "content": f"Knowledge concepts:\n\n{context}\n\n---\n\nQuestion: {question}",
    })

    url = f"{host.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": api_messages,
        "stream": True,
    }

    try:
        r = requests.post(url, json=payload, timeout=300, stream=True)
        if r.status_code == 200:
            for line in r.iter_lines():
                if line:
                    data = json.loads(line.decode("utf-8"))
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
        else:
            yield f"Error from Ollama (status code {r.status_code}): {r.text}"
    except Exception as e:
        yield f"Failed to connect to Ollama at {host}. Error: {e}"
