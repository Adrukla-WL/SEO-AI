"""
Parser Service
Handles URL parsing, metadata fetching, and content extraction.
"""

from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup

def normalize_url(base_url, link):
    """Normalizes a link to be absolute and without fragments."""
    # Make absolute
    absolute = urljoin(base_url, link)
    # Remove fragment
    defrag, _ = urldefrag(absolute)
    return defrag

def is_valid_url(url, base_domain):
    """Checks if a URL is valid and belongs to the base domain."""
    parsed = urlparse(url)
    if not parsed.scheme.startswith('http'):
        return False
    # Filter non-html extensions
    path = parsed.path.lower()
    if path.endswith(('.pdf', '.docx', '.xlsx', '.png', '.jpg', '.jpeg', '.zip')):
        return False
    # Same domain check
    if base_domain and base_domain not in parsed.netloc:
        return False
    return True

def parse_source_page(source_url: str):
    """Parses a source page for links."""
    try:
        response = requests.get(source_url, timeout=10, headers={"User-Agent": "MagicSEO/1.0"})
        response.raise_for_status()
    except Exception as e: # pylint: disable=broad-exception-caught
        return {"error": str(e), "links": []}

    soup = BeautifulSoup(response.text, 'html.parser')
    base_domain = urlparse(source_url).netloc

    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Filter garbage
        if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
            continue

        normalized = normalize_url(source_url, href)
        if is_valid_url(normalized, base_domain):
            links.add(normalized)

    return {"links": list(links), "count": len(links)}

def fetch_page_metadata(url: str):
    """Fetches title and description from a URL."""
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "MagicSEO/1.0"})
        # We process even if 404? No, raise
        if response.status_code != 200:
            return None
    except Exception: # pylint: disable=broad-exception-caught
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    title = soup.title.string.strip() if soup.title else ""

    desc_tag = soup.find('meta', attrs={'name': lambda x: x and x.lower() == 'description'})
    description = (
        desc_tag['content'].strip()
        if desc_tag and desc_tag.get('content')
        else ""
    )

    return {
        "Title": title,
        "Link": url,
        "Description": description
    }

def fetch_page_content(url: str, max_chars: int = 5000):
    """
    Fetches the body text of a page for AI context.
    """
    try:
        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "MagicSEO/1.0"}
        )
        if response.status_code != 200:
            return ""
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove scripts and styles
        for script in soup(["script", "style", "nav", "footer"]):
            script.extract()

        text = soup.get_text(separator=' ', strip=True)
        return text[:max_chars]
    except Exception: # pylint: disable=broad-exception-caught
        return ""
