
import os

from openai import OpenAI


def summarize(article, excerpt: str) -> str:
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
        model=os.getenv("GROQ_MODEL"),  # keep your existing model variable
        messages=messages,  # keep your existing messages variable
        reasoning_effort="none",
        max_completion_tokens=256,
    )

    choice = response.choices[0]
    summary = (choice.message.content or "").strip()
    
    if not summary:
        raise ValueError(
            "Groq returned empty content: "
            f"finish_reason={choice.finish_reason!r}"
        )
    
    return summary
