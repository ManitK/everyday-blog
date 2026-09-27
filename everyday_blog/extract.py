from bs4 import BeautifulSoup

from .http import get

BOILERPLATE = "nav header footer aside form script style noscript iframe .comments .comment .related .newsletter .cookie .advertisement .ad"


def limit_words(text: str, limit: int = 200) -> str:
    return " ".join(text.split()[:limit])


def useful_excerpt(existing: str) -> str:
    return limit_words(existing) if len(existing.split()) >= 25 else ""


def fetch_excerpt(client, url: str) -> tuple[str, str]:
    response = get(client, url)
    soup = BeautifulSoup(response.text, "html.parser")
    for element in soup.select(BOILERPLATE):
        element.decompose()
    container = soup.select_one("article, main, [role=main], .post-content, .entry-content") or soup.body or soup
    heading = container.select_one("h1")
    title = heading.get_text(" ", strip=True) if heading else ""
    blocks = container.select("p")
    text = " ".join(block.get_text(" ", strip=True) for block in blocks if len(block.get_text(" ", strip=True).split()) >= 4)
    return title, limit_words(text)
