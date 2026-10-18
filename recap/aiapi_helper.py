import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from environs import Env
from flask import current_app

# Optional: used for article text extraction (Step 3)
try:
    from lxml import html as lxml_html
    from readability import Document

    _HAS_READABILITY = True
except ImportError:
    Document = None
    lxml_html = None
    _HAS_READABILITY = False


class _Sentinel:
    """Falsy singleton used to signal a specific fetch outcome without being mistaken for content."""

    def __init__(self, name):
        self._name = name

    def __bool__(self):
        return False

    def __repr__(self):
        return f"<{self._name}>"


# Returned by fetch_article_content when the site actively blocks our bot (HTTP 403).
# Distinct from False ("site is down") so the task layer can treat it differently.
SITE_BLOCKED = _Sentinel("SITE_BLOCKED")


def _site_name_from_url(url):
    """Extract a human-readable site name from a URL (e.g. 'Medium' from medium.com)."""
    try:
        parts = urlparse(url).netloc.split(".")
        return parts[-2].capitalize() if len(parts) >= 2 else urlparse(url).netloc
    except Exception:
        return "Site"


_TRAILING_ID = re.compile(r"[-_](?:[0-9a-f]{8,16}|\d{4,})$")  # Medium hex ids, numeric post ids
_FILE_EXT = re.compile(r"\.(?:html?|php|aspx?)$", re.IGNORECASE)


def title_from_url(url):
    """Turn a URL slug into a lower-case title, or None if the slug is not descriptive.

    medium.com/blogflyer/12-claude-code-techniques-...-engineering-3f1ab92cc301
      → '12 claude code techniques that make ai coding feel more like engineering'
    """
    try:
        path = urlparse(url).path.rstrip("/")
    except Exception:
        return None
    slug = _FILE_EXT.sub("", path.rsplit("/", 1)[-1])
    slug = _TRAILING_ID.sub("", slug)
    words = [w for w in re.split(r"[-_+]+", slug) if w]
    if len(words) < 3:  # 'p/abc', '/2024/', etc. — not a real title
        return None
    return " ".join(words).lower()


# Max characters of article text stored on the article, and sent to the classifier.
CONTENT_STORE_MAX_CHARS = 100_000
CLASSIFY_MAX_CHARS = 12_000

# Query params that only track where a click came from; dropped so the same article saved
# twice is recognised as one URL (and long tracking strings don't overflow url_path).
_TRACKING_PARAMS = {"source", "fbclid", "gclid", "gi", "sk", "ref", "ref_src", "mc_cid", "mc_eid"}


def normalize_url(url):
    """Drop the fragment and tracking params (utm_*, source, fbclid, gclid, gi, sk, …) from a URL."""
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return url
    query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    ]
    return urlunparse(parsed._replace(query=urlencode(query), fragment=""))


def extract_article_text(html, max_chars=CONTENT_STORE_MAX_CHARS):
    """Readability-extract the main article text from raw HTML. Returns str, or None if nothing usable."""
    if not _HAS_READABILITY or not html:
        return None
    try:
        summary_html = Document(html).summary()
        if not summary_html or not summary_html.strip():
            return None
        text = lxml_html.fromstring(summary_html).text_content()
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return None
        return text[:max_chars]
    except Exception as e:
        current_app.logger.debug("extract_article_text: extraction failed: %s", e)
        return None


def fetch_article_content(url, max_chars=CONTENT_STORE_MAX_CHARS, timeout=18):
    """
    Fetch a URL and extract main article text using readability-lxml.

    Returns:
      str   — extracted text (success)
      None  — fetch succeeded but text could not be extracted
      False — site is unreachable (connection error, timeout, 5xx)
      SITE_BLOCKED — site returned 403 (bot/access blocked)
    """
    if not _HAS_READABILITY:
        current_app.logger.debug("fetch_article_content: readability not available, skipping fetch")
        return None
    try:
        response = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "Recap/1.0 (article bookmarking service)"},
        )
        response.raise_for_status()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as e:
        current_app.logger.debug("fetch_article_content: connection error for %s: %s", url, e)
        return False  # Site is unreachable
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 403:
            current_app.logger.debug("fetch_article_content: 403 bot-blocked for %s", url)
            return SITE_BLOCKED
        current_app.logger.debug("fetch_article_content: HTTP %s for %s: %s", status, url, e)
        return False  # Other HTTP errors (404, 5xx, etc.) — treat as unreachable
    except Exception as e:
        current_app.logger.debug("fetch_article_content failed for %s: %s", url, e)
        return None
    text = extract_article_text(response.text, max_chars=max_chars)
    if text is None:
        current_app.logger.debug("fetch_article_content: no article text extracted for %s", url)
    return text


class AiApiHelper:
    @staticmethod
    def ClassifyUrl(url, reference, categories=None, content=None):
        """Classify an article. Uses `content` (stored article text) when given; otherwise crawls the URL.

        When a crawl succeeds, the extracted text is returned under "fetched_content" so the caller
        can store it; site_down / site_blocked flag a failed crawl.
        """
        current_app.logger.debug(
            "AiApiHelper: calling service to classify for url: %s and reference %s", url, reference
        )
        env = Env()
        env.read_env()
        ai_url = env("RECAP_AI_API_URL") + "/classify_url"
        current_app.logger.debug("AiApiHelper: calling post to %s", ai_url)
        results_json = {}
        fetched_content = None
        if content:
            current_app.logger.debug("AiApiHelper: using stored content (%d chars), not crawling", len(content))
        else:
            content = fetch_article_content(url)
            if content:
                fetched_content = content
        site_down = content is False  # connection error / timeout / 5xx
        site_blocked = content is SITE_BLOCKED  # 403 bot-blocked
        request_data = {"url": url, "ref_key": reference, "secret": "abc123"}
        if content:  # only truthy strings (real text) reach here; sentinels are falsy
            request_data["content"] = content[:CLASSIFY_MAX_CHARS]
            request_data["skip_fetch"] = "1"  # aiapi already has the text — no need to fetch
        else:
            title_hint = title_from_url(url)
            if title_hint:
                request_data["title_hint"] = title_hint
        if site_down or site_blocked:
            # We already know the site won't serve us — stop aiapi from fetching it a second time.
            request_data["skip_fetch"] = "1"
        if categories:
            request_data["categories"] = ", ".join(categories)
            current_app.logger.debug("AiApiHelper: sending %d categories to classify", len(categories))
        try:
            r = httpx.post(ai_url, data=request_data, timeout=90)
            current_app.logger.debug("AiApiHelper: recieved results as %s", r)
            results_json = r.json()
            current_app.logger.debug("AiApiHelper: recieved results as %s", results_json)
        except httpx.HTTPError as http_err:
            current_app.logger.error(f"HTTP error occurred: {http_err}")
        except httpx.RequestError as req_err:
            current_app.logger.error(f"An error occurred while requesting: {req_err}")
        except httpx.HTTPStatusError as status_err:
            current_app.logger.error(f"Error response: {status_err}")
        except (ConnectionError, TimeoutError) as conn_err:
            current_app.logger.error(f"An error connecting to the API occurred: {conn_err}")
        except ValueError as value_err:
            current_app.logger.error(f"JSON decoding failed: {value_err}")
        except Exception as err:
            current_app.logger.error(f"An unexpected error occurred: {err}")
        if site_down:
            results_json["site_down"] = True
        if site_blocked:
            results_json["site_blocked"] = True
        if fetched_content and results_json:  # only alongside a real classification; {} still means "failed"
            results_json["fetched_content"] = fetched_content
        return results_json

    @staticmethod
    def EmbedText(text: str):
        current_app.logger.debug("AiApiHelper: embedding text of length %d", len(text))
        env = Env()
        env.read_env()
        ai_url = env("RECAP_AI_API_URL") + "/embed"
        try:
            r = httpx.post(ai_url, data={"text": text, "secret": "abc123"}, timeout=30)
            result = r.json()
            return result.get("embedding")
        except httpx.HTTPError as http_err:
            current_app.logger.error(f"HTTP error occurred: {http_err}")
        except httpx.RequestError as req_err:
            current_app.logger.error(f"An error occurred while requesting: {req_err}")
        except (ConnectionError, TimeoutError) as conn_err:
            current_app.logger.error(f"An error connecting to the API occurred: {conn_err}")
        except ValueError as value_err:
            current_app.logger.error(f"JSON decoding failed: {value_err}")
        except Exception as err:
            current_app.logger.error(f"An unexpected error occurred: {err}")
        return None

    @staticmethod
    def PerformTask(context, prompt, format, ref_key):
        current_app.logger.debug(
            "AiApiHelper: calling service to perform task for context: %s, prompt: %s, format: %s, ref_key: %s",
            context,
            prompt,
            format,
            ref_key,
        )
        env = Env()
        env.read_env()
        results_json = {}
        ai_url = env("RECAP_AI_API_URL") + "/process_task"
        current_app.logger.debug("AiApiHelper: calling post to %s", ai_url)
        request_data = {"context": context, "prompt": prompt, "format": format, "secret": "abc123", "ref_key": ref_key}
        try:
            r = httpx.post(ai_url, data=request_data, timeout=180)
            results_json = r.json()
            current_app.logger.debug("AiApiHelper: recieved results as %s", results_json)
        except httpx.HTTPError as http_err:
            current_app.logger.error(f"HTTP error occurred: {http_err}")
        except httpx.RequestError as req_err:
            current_app.logger.error(f"An error occurred while requesting: {req_err}")
        except httpx.HTTPStatusError as status_err:
            current_app.logger.error(f"Error response: {status_err}")
        except (ConnectionError, TimeoutError) as conn_err:
            current_app.logger.error(f"An error connecting to the API occurred: {conn_err}")
        except ValueError as value_err:
            current_app.logger.error(f"JSON decoding failed: {value_err}")
        except Exception as err:
            current_app.logger.error(f"An unexpected error occurred: {err}")
        return results_json
