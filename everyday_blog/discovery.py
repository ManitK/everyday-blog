from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .http import get
from .models import Article

LOG = logging.getLogger(__name__)


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date_parser.parse(value, fuzzy=True)
        return parsed if parsed.tzinfo else parsed.astimezone()
    except (TypeError, ValueError, OverflowError):
        return None


def _text(value: str) -> str:
    return " ".join(BeautifulSoup(value or "", "html.parser").stripped_strings)


def discover_feed(client, blog: dict) -> list[Article]:
    body = get(client, blog["feed_url"]).content
    feed = feedparser.parse(body)
    if feed.bozo and not feed.entries:
        raise ValueError(f"unreadable feed: {feed.bozo_exception}")
    articles = []
    for entry in feed.entries:
        published = parse_date(entry.get("published") or entry.get("updated"))
        url = entry.get("link")
        title = _text(entry.get("title", ""))
        if published and url and title:
            articles.append(Article(title, url, published, blog["name"], _text(entry.get("summary", ""))))
    return articles


def discover_sitemap(client, blog: dict) -> list[Article]:
    root = ET.fromstring(get(client, blog["sitemap_url"]).content)
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    if root.tag.endswith("sitemapindex"):
        raise ValueError("sitemap index is not supported; configure a post sitemap URL")
    articles = []
    for node in root.findall(f"{namespace}url"):
        loc = node.findtext(f"{namespace}loc")
        published = parse_date(node.findtext(f"{namespace}lastmod"))
        if loc and published:
            # A sitemap lacks titles; this readable fallback is replaced by page title when fetched.
            title = re.sub(r"[-_/]+", " ", loc.rstrip("/").rsplit("/", 1)[-1]).strip() or loc
            articles.append(Article(title, loc, published, blog["name"]))
    return articles


def discover_html(client, blog: dict) -> list[Article]:
    spec = blog.get("html") or {}
    selector = spec.get("article_selector", "article")
    soup = BeautifulSoup(get(client, blog["url"]).text, "html.parser")
    articles = []
    for node in soup.select(selector):
        link = node if node.name == "a" and node.get("href") else node.select_one(spec.get("link_selector", "a[href]"))
        date_node = node.select_one(spec.get("date_selector", "time"))
        title_node = node.select_one(spec.get("title_selector", "h1, h2, h3"))
        published = parse_date((date_node.get("datetime") if date_node else None) or (date_node.get_text(" ") if date_node else None))
        if link and title_node and published and link.get("href"):
            articles.append(Article(_text(str(title_node)), urljoin(blog["url"], link["href"]), published, blog["name"]))
    return articles


def _nested(data: dict, path: str):
    value = data
    for part in path.split("."):
        value = value[part]
    return value


def discover_next_data(client, blog: dict) -> list[Article]:
    """Discover posts from public Next.js __NEXT_DATA__ JSON using configuration."""
    spec = blog["next_data"]
    soup = BeautifulSoup(get(client, blog["url"]).text, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        raise ValueError("page has no __NEXT_DATA__ JSON")
    payload = json.loads(tag.string)
    articles = []
    for entry in _nested(payload, spec["items_path"]):
        published = parse_date(entry.get(spec["date_key"]))
        title = _text(str(entry.get(spec["title_key"], "")))
        url_value = entry.get(spec["url_key"], "")
        if published and title and url_value:
            url = urljoin(blog["url"], spec.get("url_prefix", "") + url_value)
            excerpt = _text(str(entry.get(spec.get("excerpt_key", "summary"), "")))
            articles.append(Article(title, url, published, blog["name"], excerpt))
    return articles


def discover(client, blog: dict) -> list[Article]:
    page_discovery = discover_next_data if blog.get("next_data") else discover_html
    methods = (("feed_url", discover_feed), ("sitemap_url", discover_sitemap), ("url", page_discovery))
    failures = []
    for required_key, method in methods:
        if required_key not in blog:
            continue
        try:
            found = method(client, blog)
            LOG.info("%s: discovered %d posts through %s", blog["name"], len(found), method.__name__.removeprefix("discover_"))
            return found
        except Exception as exc:
            failures.append(f"{method.__name__}: {exc}")
            LOG.warning("%s discovery failed via %s: %s", blog["name"], method.__name__, exc)
    raise RuntimeError("all configured discovery methods failed: " + "; ".join(failures))
