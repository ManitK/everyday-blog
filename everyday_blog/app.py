import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from .claude import summarize
from .discovery import discover
from .extract import fetch_excerpt, useful_excerpt
from .http import session
from .models import Article
from .notify import digest, send
from .state import load, save

LOG = logging.getLogger(__name__)


def load_local_env(path: Path = Path(".env")) -> None:
    """Load simple KEY=value entries from the ignored local .env file.

    Existing environment variables win, so CI can continue to supply secrets normally.
    """
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def process_article(article: Article, timeout: int):
    """Fetch context and summarize one article; safe to run independently in a worker."""
    try:
        excerpt = useful_excerpt(article.excerpt)
        page_title = ""
        if not excerpt:
            # Sessions are not shared across threads.
            page_title, excerpt = fetch_excerpt(session(timeout), article.url)
        if not excerpt:
            raise ValueError("no meaningful article excerpt found")
        article = Article(page_title or article.title, article.url, article.published_at, article.source, excerpt)
        return article, summarize(article, excerpt), None
    except Exception as exc:
        return None, None, (article.url, exc)


def run(config_path: str = "config.yaml", state_path: str = "state.json") -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_local_env()
    config = yaml.safe_load(Path(config_path).read_text()) or {}
    blogs = config.get("blogs", [])
    if not blogs:
        LOG.error("No blogs configured in %s", config_path)
        return 2
    previous = load(Path(state_path))
    started = datetime.now().astimezone()
    overlap = timedelta(minutes=config.get("overlap_minutes", 0))
    cutoff = previous - overlap if previous else started
    timeout = int(config.get("request_timeout_seconds", 20))
    client = session(timeout)
    failures = []
    new_articles: list[Article] = []
    for blog in blogs:
        try:
            found = discover(client, blog)
            new_articles.extend(article for article in found if article.published_at > cutoff)
        except Exception as exc:
            failures.append(blog["name"])
            LOG.exception("Skipping failed blog %s: %s", blog["name"], exc)
    # First run establishes a baseline; it intentionally never sends an unexpected historical flood.
    if previous is None and not failures:
        save(Path(state_path), started)
        LOG.info("Initialized state; future articles will be included")
        return 0
    # Deduplicate a post exposed by two entries, then cap surprising feeds.
    by_url = {article.url: article for article in new_articles}
    selected = sorted(by_url.values(), key=lambda a: a.published_at)[:int(config.get("max_articles_per_blog", 20)) * len(blogs)]
    items = []
    workers = max(1, int(config.get("article_workers", 4)))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="article") as executor:
        results = executor.map(lambda article: process_article(article, timeout), selected)
        for article, summary, error in results:
            if error:
                url, exc = error
                failures.append(url)
                LOG.error("Could not summarize %s: %s", url, exc)
            else:
                items.append((article, summary))
    if failures:
        LOG.error("Run incomplete (%s); state is deliberately unchanged", ", ".join(failures))
        return 1
    if items:
        try:
            send(client, digest(items))
        except Exception as exc:
            LOG.exception("Could not deliver digest; state is deliberately unchanged: %s", exc)
            return 1
        LOG.info("Sent digest containing %d articles", len(items))
    else:
        LOG.info("No new articles; no notification sent")
    save(Path(state_path), started)
    LOG.info("Saved successful-run timestamp")
    return 0
