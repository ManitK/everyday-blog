import os
from urllib.parse import urlparse

MAX_MESSAGE_BYTES = 3_600


def _section(article, summary: str) -> str:
    # Raw HTTPS URLs are tappable in ntfy's native clients without Markdown.
    return f"{article.source}\n{article.title}\n\n{summary}\n\n🔗 {article.url}"


def _minimal_section(article, title: str) -> str:
    return f"{title}\n🔗 {article.url}"


def _shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rsplit(" ", 1)[0] + "…"


def digest(items: list[tuple[object, str]]) -> str:
    heading = ["📰 Daily Blog Update", f"{len(items)} new article{'s' if len(items) != 1 else ''}"]
    body = "\n\n".join(heading + [_section(article, summary) for article, summary in items])
    if len(body.encode()) <= MAX_MESSAGE_BYTES:
        return body

    # ntfy's public service has a small normal-message limit. Keep every title
    # and tappable URL, allocating the remaining space evenly to concise gists.
    fixed = "\n\n".join(heading + [_section(article, "") for article, _ in items])
    if len(fixed.encode()) <= MAX_MESSAGE_BYTES:
        summary_limit = max(0, (MAX_MESSAGE_BYTES - len(fixed.encode())) // max(1, len(items)))
        return "\n\n".join(heading + [_section(article, _shorten(summary, summary_limit)) for article, summary in items])

    # An unusually link-heavy digest still retains every tappable URL. Sources
    # and gists are omitted only when they cannot fit in one normal message.
    url_bytes = sum(len(article.url.encode()) + 5 for article, _ in items)
    title_limit = max(0, (MAX_MESSAGE_BYTES - url_bytes - len("\n\n".join(heading).encode())) // max(1, len(items)))
    while True:
        compact = "\n\n".join(heading + [_minimal_section(article, _shorten(article.title, title_limit)) for article, _ in items])
        if len(compact.encode()) <= MAX_MESSAGE_BYTES or title_limit == 0:
            return compact
        title_limit -= 1


def send(client, message: str) -> None:
    configured_topic = os.environ["NTFY_TOPIC"].strip()
    # Accept either the preferred bare topic or a copied https://ntfy.sh/topic URL.
    if configured_topic.startswith(("http://", "https://")):
        parsed = urlparse(configured_topic)
        if parsed.netloc != "ntfy.sh" or not parsed.path.strip("/"):
            raise ValueError("NTFY_TOPIC must be a topic name or an https://ntfy.sh/<topic> URL")
        topic = parsed.path.strip("/")
    else:
        topic = configured_topic.strip("/")
    if not topic or "/" in topic:
        raise ValueError("NTFY_TOPIC must contain one non-empty topic name")
    # The JSON API explicitly publishes a message rather than an uploaded body.
    response = client.post(
        "https://ntfy.sh",
        json={
            "topic": topic,
            "message": message,
            "title": "Daily Blog Update",
            "tags": ["newspaper"],
        },
        timeout=client.request_timeout,  # type: ignore[attr-defined]
    )
    response.raise_for_status()
