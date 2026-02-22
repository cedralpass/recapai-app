import re
import functools
import json
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, jsonify, current_app, logging
)
from werkzeug.exceptions import abort
from openai import OpenAI
from aiapi.config import AIAPIConfig

try:
    import httpx
    from readability import Document
    from lxml import html as lxml_html
    _HAS_READABILITY = True
except ImportError:
    httpx = None
    Document = None
    lxml_html = None
    _HAS_READABILITY = False

bp = Blueprint('classify', __name__)


def fetch_article_content(url, max_chars=12000, timeout=18):
    """
    Fetch a URL and extract main article text. Returns plain text truncated to max_chars, or None on failure.
    Used when content is not passed in the request (fallback so classification can use real article text).
    """
    if not _HAS_READABILITY or not url:
        if not _HAS_READABILITY:
            current_app.logger.warning(
                "classify: readability not available (install readability-lxml and lxml); "
                "content fetch skipped. Rebuild image with libxml2-dev/libxslt-dev on Alpine."
            )
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

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        key = extract_from_request('secret')
        if key is None:
            return jsonify("Not Authorized"), 401
        return view(**kwargs)

    return wrapped_view

@bp.route('/classify_url',methods=('GET', 'POST'))
@login_required
def classify_url():
    url = None
    ref_key = None
    url = extract_from_request('url')
    ref_key = extract_from_request('ref_key')
    content = request.form.get('content')
    if content is not None and isinstance(content, str):
        content = content.strip() or None
    else:
        content = None

    # If content was not passed in the form, try to fetch and extract it here (fallback)
    if not content and url:
        current_app.logger.debug("classify: no content in request, fetching url for fallback: %s", url)
        content = fetch_article_content(url)
        if content:
            current_app.logger.debug("classify: fallback fetch succeeded, using %d chars", len(content))
        else:
            current_app.logger.debug("classify: fallback fetch returned no content, using URL-only prompt")
    elif content:
        current_app.logger.debug("classify: using content from request (%d chars)", len(content))

    json_return={}

    #create OpenAI request
    client = OpenAI(api_key=current_app.config["AI_API_OPENAI"])

    #make OpenAI Call
    response = client.chat.completions.create(
        model=AIAPIConfig.AI_OPEN_AI_MODEL,
        messages=build_prompt(url, content=content),
        response_format={"type": "json_object"},
        temperature=0.25,
        max_tokens=512,
        frequency_penalty=0.15,
        presence_penalty=0
    )
    
    if len(response.choices)>=1:
        current_app.logger.info("classify: recieved response with >=1 choice from OpenAI")
        current_app.logger.debug(response.choices[0].message.content)
        json_return = response.choices[0].message.content
        current_app.logger.info("model %s cost %s", response.model, response.usage)
    else:
        current_app.logger.error("error: with openAPI call. no choices returned %s", response)

    response_json = json.loads(json_return)
    if ref_key is not None:
        response_json['ref_key']=ref_key
        current_app.logger.debug("classify: added ref_key to response: " + ref_key)
    else:
        current_app.logger.error("error: missing ref_key")
    
    current_app.logger.debug("classify: full response " + str(response_json))
    return jsonify(response_json)

def extract_from_request(key):
    value=None
    current_app.logger.debug("classify: request form keys: " + str(request.form.keys()))
    value = request.form.get(key)
    if value is None:
        current_app.logger.error("error: must supply url and secret for url for classification.  Supply a ref_key for refeference to an object.")
        current_app.logger.debug("extract_from_request: value to missing for %s with value", key)
    return value

def build_prompt(url, content=None):
    if content:
        system_content = (
            "You are given the URL and the full article text below. Classify the article based only on the provided text. "
            "Using these content categories as examples: Software Architecture, Leadership, Business Strategy, and Artificial Intelligence. "
            "If the content does not fit a category, recommend a new category. "
            "Base your summary, key_topics, sub_categories, author, and title only on the provided text; do not invent information. "
            "Respond with: category, url of blog, blog title, author, a short summary, "
            "three key topics as bullet points, and three sub categories as bullet points. "
            "Respond in a structured JSON with keys: author, blog_title, category, summary, key_topics, sub_categories, url."
        )
        user_content = f"Classify the following article. URL: {url}\n\nArticle text:\n\n{content}"
    else:
        system_content = (
            "You are given ONLY the URL of a blog post; the article text is not provided. "
            "Using these content categories as examples: Software Architecture, Leadership, Business Strategy, and Artificial Intelligence. "
            "If the content does not fit a category, recommend a new category. "
            "Do NOT invent or assume acronym meanings, author, title, or details. "
            "If you cannot infer something from the URL alone, use a neutral placeholder (e.g. 'Unknown' or 'From URL only'). "
            "Respond with: category, url of blog, blog title, author, a short summary (based only on what the URL suggests; do not invent content), "
            "three key topics as bullet points, and three sub categories as bullet points. "
            "Respond in a structured JSON with keys: author, blog_title, category, summary, key_topics, sub_categories, url."
        )
        user_content = "please classify this blog post: " + str(url)
    prompt_string = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content}
    ]
    current_app.logger.debug("prompt to classify: %s", prompt_string)
    return prompt_string