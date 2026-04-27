import re
import httpx
from environs import Env
from flask import current_app

# Optional: used for article text extraction (Step 3)
try:
    from readability import Document
    from lxml import html as lxml_html
    _HAS_READABILITY = True
except ImportError:
    Document = None
    lxml_html = None
    _HAS_READABILITY = False


def fetch_article_content(url, max_chars=12000, timeout=18):
    """
    Fetch a URL and extract main article text using readability-lxml.
    Returns plain text truncated to max_chars, or None on any failure.
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
        doc = Document(response.text)
        summary_html = doc.summary()
        if not summary_html or not summary_html.strip():
            current_app.logger.debug("fetch_article_content: empty summary for %s", url)
            return None
        tree = lxml_html.fromstring(summary_html)
        text = tree.text_content()
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return None
        if len(text) > max_chars:
            text = text[:max_chars]
        return text
    except Exception as e:
        current_app.logger.debug("fetch_article_content failed for %s: %s", url, e)
        return None


class AiApiHelper:
    @staticmethod
    def ClassifyUrl(url, reference):
        current_app.logger.debug("AiApiHelper: calling service to classify for url: %s and reference %s", url, reference)
        env = Env()
        env.read_env()
        ai_url = env("RECAP_AI_API_URL")+"/classify_url"
        current_app.logger.debug('AiApiHelper: calling post to %s', ai_url)
        results_json = {}
        content = fetch_article_content(url)
        request_data = {'url': url, 'ref_key': reference, 'secret': "abc123"}
        if content:
            request_data['content'] = content
        try:
            r = httpx.post(ai_url, data=request_data, timeout=90)
            current_app.logger.debug("AiApiHelper: recieved results as %s", r)
            results_json = r.json()
            current_app.logger.debug("AiApiHelper: recieved results as %s", results_json)
        except httpx.HTTPError as http_err:
            current_app.logger.error(f'HTTP error occurred: {http_err}')
        except httpx.RequestError as req_err:
            current_app.logger.error(f'An error occurred while requesting: {req_err}')
        except httpx.HTTPStatusError as status_err:
            current_app.logger.error(f'Error response: {status_err}')
        except (ConnectionError, TimeoutError) as conn_err:
            current_app.logger.error(f'An error connecting to the API occurred: {conn_err}')
        except ValueError as value_err:
            current_app.logger.error(f'JSON decoding failed: {value_err}')
        except Exception as err:
            current_app.logger.error(f'An unexpected error occurred: {err}')
        return results_json
    
    @staticmethod
    def PerformTask(context, prompt, format, ref_key):
        current_app.logger.debug("AiApiHelper: calling service to perform task for context: %s, prompt: %s, format: %s, ref_key: %s", context, prompt, format, ref_key)
        env = Env()
        env.read_env()
        results_json={}
        ai_url = env("RECAP_AI_API_URL")+"/process_task"
        current_app.logger.debug('AiApiHelper: calling post to %s', ai_url)
        request_data = {'context': context, 'prompt': prompt, 'format': format, 'secret': "abc123", 'ref_key': ref_key}
        try:
            r = httpx.post(ai_url, data=request_data, timeout=120)
            results_json = r.json()
            current_app.logger.debug("AiApiHelper: recieved results as %s", results_json)
        except httpx.HTTPError as http_err:
            current_app.logger.error(f'HTTP error occurred: {http_err}')
        except httpx.RequestError as req_err:
            current_app.logger.error(f'An error occurred while requesting: {req_err}')
        except httpx.HTTPStatusError as status_err:
            current_app.logger.error(f'Error response: {status_err}')
        except (ConnectionError, TimeoutError) as conn_err:
            current_app.logger.error(f'An error connecting to the API occurred: {conn_err}')
        except ValueError as value_err:
            current_app.logger.error(f'JSON decoding failed: {value_err}')
        except Exception as err:
            current_app.logger.error(f'An unexpected error occurred: {err}')
        return results_json
    
    