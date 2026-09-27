import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def session(timeout: int) -> requests.Session:
    client = requests.Session()
    retries = Retry(
        total=3, connect=3, read=3, status=3, backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET", "POST"),
    )
    client.mount("https://", HTTPAdapter(max_retries=retries))
    client.headers["User-Agent"] = "everyday-blog/1.0 (+local personal digest)"
    client.request_timeout = timeout  # type: ignore[attr-defined]
    return client


def get(client: requests.Session, url: str) -> requests.Response:
    response = client.get(url, timeout=client.request_timeout)  # type: ignore[attr-defined]
    response.raise_for_status()
    return response
