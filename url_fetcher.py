"""
url_fetcher.py — Web content scraper for VeriNews
Retrieves text and metadata from submitted URLs.
"""
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 15  # seconds
MAX_TEXT_LENGTH = 20000  # characters


def _extract_author(soup: BeautifulSoup) -> str:
    """Attempt to extract author from common meta tags."""
    candidates = [
        soup.find("meta", attrs={"name": "author"}),
        soup.find("meta", attrs={"property": "article:author"}),
        soup.find("meta", attrs={"name": "twitter:creator"}),
    ]
    for tag in candidates:
        if tag and tag.get("content"):
            return tag["content"].strip()

    # Try schema.org author
    author_el = soup.find(attrs={"itemprop": "author"})
    if author_el:
        return author_el.get_text(strip=True)

    return "Unknown"


def _extract_date(soup: BeautifulSoup) -> str:
    """Attempt to extract publish date from common meta tags."""
    candidates = [
        soup.find("meta", attrs={"property": "article:published_time"}),
        soup.find("meta", attrs={"name": "publish-date"}),
        soup.find("meta", attrs={"name": "date"}),
        soup.find("time"),
    ]
    for tag in candidates:
        if tag:
            val = tag.get("content") or tag.get("datetime") or tag.get_text(strip=True)
            if val:
                return val[:30]
    return "Unknown"


def _extract_body(soup: BeautifulSoup) -> str:
    """Extract main body text, preferring <article> or <main>."""
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    body_el = soup.find("article") or soup.find("main") or soup.find("body")
    if body_el:
        text = body_el.get_text(separator=' ')
    else:
        text = soup.get_text(separator=' ')

    # Normalise whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:MAX_TEXT_LENGTH]


def fetch_url(url: str) -> dict:
    """
    Fetch a URL and return extracted content.

    Returns:
        {
            "original_url": str,
            "author": str,
            "post_date": str,
            "fetched_text": str,
            "fetch_status": "success" | "failed",
            "error": str | None
        }
    """
    result = {
        "original_url": url,
        "author": "Unknown",
        "post_date": "Unknown",
        "fetched_text": "",
        "fetch_status": "failed",
        "error": None
    }

    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url

        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        result["author"] = _extract_author(soup)
        result["post_date"] = _extract_date(soup)
        result["fetched_text"] = _extract_body(soup)
        result["fetch_status"] = "success"

        logger.info(f"[URL] Fetched {len(result['fetched_text'])} chars from {url}")

    except requests.exceptions.RequestException as e:
        result["error"] = str(e)
        result["fetch_status"] = "failed"
        logger.warning(f"[URL] Fetch failed for {url}: {e}")

    except Exception as e:
        result["error"] = str(e)
        result["fetch_status"] = "failed"
        logger.exception(f"[URL] Unexpected error for {url}")

    return result
