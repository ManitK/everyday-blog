
import os

from openai import OpenAI


def summarize(article, excerpt: str) -> str:
    """Generate a concise article gist using Groq's GPT-OSS 120B."""
    client = OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
        max_retries=2,
        timeout=30.0,
    )

    prompt = f"""Explain what this article is actually about in 1–2
concise sentences, using simple everyday language for someone
with no prior context. Briefly explain unavoidable technical
terms. Focus on the main idea, not just the topic.
Use only the supplied context; do not invent missing facts.
Return plain text only.

Source: {article.source}
Title: {article.title}
URL: {article.url}

Excerpt:
{excerpt}"""

    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_completion_tokens=140,
        temperature=0,
    )

    summary = response.choices[0].message.content
    if not summary or not summary.strip():
        raise ValueError("Groq returned an empty summary")

    return summary.strip()
