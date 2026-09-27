from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    published_at: datetime
    source: str
    excerpt: str = ""
