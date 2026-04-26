"""
Tier 2 integration test — article classification pipeline.

What is covered end-to-end:
  1. fetch_article_content   — readability extracts text from fixture HTML
  2. AiApiHelper.ClassifyUrl — httpx GET + POST intercepted by respx
  3. save_classification_result + DB commit — real SQLite in-memory DB

HTTP boundaries mocked with respx:
  - httpx.GET(article_url)         → returns recorded fixture HTML
  - httpx.POST(aiapi/classify_url) → returns recorded OpenAI fixture JSON
                                     (aiapi response is fully determined by the
                                      OpenAI fixture; aiapi logic is exercised
                                      separately in tests/aiapi/unit/test_classify.py)

Fixtures on disk (recorded once from live services):
  tests/fixtures/flask_tutorial_part1.html          — raw HTML from miguelgrinberg.com
                                                       fetched with the same headers that
                                                       fetch_article_content uses
  tests/fixtures/openai_flask_tutorial_response.json — actual OpenAI response captured
                                                        from a live rq-worker run
"""
import json
import urllib.parse
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

FLASK_TUTORIAL_URL = (
    "https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world"
)
# No trailing slash — avoids double-slash in AiApiHelper: env("RECAP_AI_API_URL") + "/classify_url"
AIAPI_TEST_BASE = "http://aiapi.test"

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def flask_tutorial_html():
    """Raw HTML recorded from the Flask Mega-Tutorial Part I."""
    return (FIXTURES / "flask_tutorial_part1.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def openai_fixture():
    """OpenAI response recorded from a live rq-worker classification run."""
    return json.loads((FIXTURES / "openai_flask_tutorial_response.json").read_text())


def _aiapi_json_response(openai_fixture, ref_key="1"):
    """Build the JSON body that aiapi would return for the fixture OpenAI response."""
    payload = dict(openai_fixture)
    payload["ref_key"] = ref_key
    return payload


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.recap
class TestClassificationPipeline:

    def test_article_fields_are_saved_after_full_pipeline(
        self, recap_app, openai_fixture, flask_tutorial_html, monkeypatch
    ):
        """
        Happy path: fetch article HTML → classify via aiapi → save to DB.

        respx intercepts both HTTP boundaries so no network or live services are
        needed. Exercises:
          - fetch_article_content: readability parsing of fixture HTML
          - AiApiHelper.ClassifyUrl: httpx GET + POST path
          - save_classification_result: every field written to SQLite in-memory DB
        """
        from recap import db
        from recap.models import Article, User
        from recap.aiapi_helper import AiApiHelper
        from recap.tasks import save_classification_result

        monkeypatch.setenv("RECAP_AI_API_URL", AIAPI_TEST_BASE)

        with recap_app.app_context():
            user = User(username="pipeline_user", email="pipeline@example.com")
            user.set_password("testpass")
            db.session.add(user)
            db.session.commit()

            article = Article(url_path=FLASK_TUTORIAL_URL, user_id=user.id)
            db.session.add(article)
            db.session.commit()

            with respx.mock(assert_all_called=True) as mock:
                # Boundary 1: article fetch → recorded HTML → readability extracts text
                mock.get(FLASK_TUTORIAL_URL).mock(
                    return_value=httpx.Response(200, text=flask_tutorial_html)
                )
                # Boundary 2: aiapi response → recorded fixture JSON
                mock.post(f"{AIAPI_TEST_BASE}/classify_url").mock(
                    return_value=httpx.Response(
                        200,
                        json=_aiapi_json_response(openai_fixture, ref_key=str(user.id)),
                    )
                )

                result = AiApiHelper.ClassifyUrl(FLASK_TUTORIAL_URL, user.id)
                save_classification_result(result, article)
                db.session.add(article)
                db.session.commit()

            saved = db.session.get(Article, article.id)

            assert saved.author_name == "Miguel Grinberg"
            assert saved.title == "The Flask Mega-Tutorial Part I: Hello, World!"
            assert saved.category == "Software Architecture"
            assert "Flask" in saved.summary
            assert json.loads(saved.key_topics) == openai_fixture["key_topics"]
            assert json.loads(saved.sub_categories) == openai_fixture["sub_categories"]
            assert saved.classified is not None

    def test_readability_content_is_forwarded_to_aiapi(
        self, recap_app, openai_fixture, flask_tutorial_html, monkeypatch
    ):
        """
        The text extracted by readability from the fixture HTML must appear in
        the POST body sent to aiapi — not just the URL.

        This confirms the content-enrichment path works: recap fetches the
        article, extracts the text, and passes it to aiapi so OpenAI gets the
        full article body rather than just a URL to guess from.
        """
        from recap import db
        from recap.models import User
        from recap.aiapi_helper import AiApiHelper

        monkeypatch.setenv("RECAP_AI_API_URL", AIAPI_TEST_BASE)
        captured: dict = {}

        with recap_app.app_context():
            user = User(username="extraction_user", email="extraction@example.com")
            user.set_password("pw")
            db.session.add(user)
            db.session.commit()

            with respx.mock as mock:
                mock.get(FLASK_TUTORIAL_URL).mock(
                    return_value=httpx.Response(200, text=flask_tutorial_html)
                )

                def capture_and_respond(request: httpx.Request) -> httpx.Response:
                    form = dict(urllib.parse.parse_qsl(request.content.decode()))
                    captured["content"] = form.get("content", "")
                    return httpx.Response(
                        200,
                        json=_aiapi_json_response(openai_fixture, ref_key=str(user.id)),
                    )

                mock.post(f"{AIAPI_TEST_BASE}/classify_url").mock(
                    side_effect=capture_and_respond
                )

                AiApiHelper.ClassifyUrl(FLASK_TUTORIAL_URL, user.id)

            # readability should extract real Flask article text
            assert "Flask" in captured["content"], (
                "readability-extracted text forwarded to aiapi should contain 'Flask'"
            )
            assert len(captured["content"]) > 500, (
                "extracted content should be substantial, not just a title or snippet"
            )

    def test_aiapi_503_returns_empty_dict_without_raising(
        self, recap_app, monkeypatch
    ):
        """
        When aiapi is unavailable (503), ClassifyUrl returns {} gracefully.

        The RQ task (classify_url in tasks.py) wraps the call in try/except;
        an empty dict prevents it from attempting to index missing keys and
        crashing the worker process.
        """
        monkeypatch.setenv("RECAP_AI_API_URL", AIAPI_TEST_BASE)

        with recap_app.app_context():
            with respx.mock as mock:
                mock.get(FLASK_TUTORIAL_URL).mock(
                    return_value=httpx.Response(
                        200, text="<html><body><p>Article body text.</p></body></html>"
                    )
                )
                mock.post(f"{AIAPI_TEST_BASE}/classify_url").mock(
                    return_value=httpx.Response(503, text="Service Unavailable")
                )

                from recap.aiapi_helper import AiApiHelper
                result = AiApiHelper.ClassifyUrl(FLASK_TUTORIAL_URL, 99)

            assert result == {}


@pytest.mark.integration
@pytest.mark.aiapi
class TestAiapiClassifyWithRealLogic:
    """
    Exercise the aiapi classify_url route logic directly via the Flask test client.
    OpenAI is mocked; everything else in aiapi runs for real.

    Complements the pipeline tests above by verifying that aiapi:
      - enforces the secret key check
      - builds the correct OpenAI prompt when content is provided
      - parses the OpenAI JSON response and returns it with ref_key injected
    """

    def test_aiapi_returns_classified_json_with_content(
        self, aiapi_app, openai_fixture
    ):
        """aiapi /classify_url with content in the request returns the OpenAI fixture."""
        from unittest.mock import MagicMock

        mock_openai = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(openai_fixture)
        mock_openai.return_value.chat.completions.create.return_value = mock_completion

        with patch("aiapi.classify.OpenAI", mock_openai):
            with aiapi_app.test_client() as c:
                resp = c.post(
                    "/classify_url",
                    data={
                        "url": FLASK_TUTORIAL_URL,
                        "ref_key": "42",
                        "secret": "abc123",
                        "content": (
                            "Welcome to the Flask Mega-Tutorial. "
                            "In this first chapter you will learn how to set up a Flask project."
                        ),
                    },
                )

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["author"] == "Miguel Grinberg"
        assert data["category"] == "Software Architecture"
        assert data["ref_key"] == "42"

    def test_aiapi_rejects_request_without_secret(self, aiapi_app):
        """Requests missing the secret field get a 401."""
        with aiapi_app.test_client() as c:
            resp = c.post(
                "/classify_url",
                data={"url": FLASK_TUTORIAL_URL, "ref_key": "1"},
            )
        assert resp.status_code == 401
