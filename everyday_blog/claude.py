import os

from anthropic import Anthropic


def summarize(article, excerpt: str) -> str:
    # Construct exactly one API request per invocation. Caller invokes this once per new article.
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=3)
    prompt = f"""Give a concise 1–2 sentence gist of this article. Explain what it is actually about and its main idea in simple, everyday language for someone with no prior context. Briefly explain unavoidable technical terms. Use only the supplied context; do not infer missing facts. Return plain text only.\n\nSource: {article.source}\nTitle: {article.title}\nURL: {article.url}\nExcerpt (limited context):\n{excerpt}"""
    response = client.messages.create(
        model=os.getenv("CLAUDE_MODEL") or "claude-haiku-4-5-20251001",
        max_tokens=140,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return " ".join(block.text for block in response.content if block.type == "text").strip()
