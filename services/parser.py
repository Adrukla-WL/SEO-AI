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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        response = requests.get(source_url, timeout=10, headers=headers)
        response.raise_for_status()
    except Exception as e: # pylint: disable=broad-exception-caught
        return {"error": f"Ошибка запроса: {str(e)}", "links": []}

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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    }
    try:
        response = requests.get(url, timeout=10, headers=headers)
        # We process even if 404? No, raise
        if response.status_code != 200:
            return None
    except Exception: # pylint: disable=broad-exception-caught
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    if not title:
        # Fallback to h1 or url
        h1 = soup.find('h1')
        title = h1.text.strip() if h1 else url

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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    }
    try:
        response = requests.get(
            url,
            timeout=10,
            headers=headers
        )
        if response.status_code != 200:
            return ""
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove scripts and styles
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()

        text = soup.get_text(separator=' ', strip=True)
        return text[:max_chars]
    except Exception: # pylint: disable=broad-exception-caught
        return ""
