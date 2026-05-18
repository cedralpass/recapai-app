"""Unit tests for AiApiHelper and fetch_article_content (Step 3 content fetch)."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@pytest.mark.recap
class TestFetchArticleContent:
    """Tests for fetch_article_content helper."""

    @patch("recap.aiapi_helper._HAS_READABILITY", True)
    @patch("recap.aiapi_helper.lxml_html")
    @patch("recap.aiapi_helper.Document")
    @patch("recap.aiapi_helper.httpx")
    def test_returns_extracted_text_when_fetch_succeeds(self, mock_httpx, mock_document, mock_lxml_html, recap_app):
        """When GET and readability succeed, return extracted text (truncated to max_chars)."""
        mock_response = MagicMock()
        mock_response.text = "<html/>"
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        mock_doc_instance = MagicMock()
        mock_doc_instance.summary.return_value = "<p>Hello world. " + "x" * 20000 + "</p>"
        mock_document.return_value = mock_doc_instance

        mock_tree = MagicMock()
        mock_tree.text_content.return_value = "Hello world. " + "x" * 20000
        mock_lxml_html.fromstring.return_value = mock_tree

        with recap_app.app_context():
            from recap.aiapi_helper import fetch_article_content

            result = fetch_article_content("https://example.com/article", max_chars=12000)
        assert result is not None
        assert "Hello world" in result
        assert len(result) <= 12000

    @patch("recap.aiapi_helper._HAS_READABILITY", True)
    def test_returns_none_when_http_fails(self, recap_app):
        """Generic httpx.RequestError (not a ConnectError/Timeout) falls through to None.

        Only specific subclasses (ConnectError, TimeoutException, HTTPStatusError) return False.
        A bare RequestError (e.g. TooManyRedirects) returns None because it's ambiguous.
        """
        import httpx

        with patch("recap.aiapi_helper.httpx.get", side_effect=httpx.RequestError("connection failed")):
            with recap_app.app_context():
                from recap.aiapi_helper import fetch_article_content

                result = fetch_article_content("https://example.com/article")
        assert result is None

    @patch("recap.aiapi_helper._HAS_READABILITY", True)
    def test_returns_false_for_connect_error_modeling_cq2co_dns_failure(self, recap_app):
        """ConnectError (DNS lookup failure, as observed with cq2.co) returns False.

        False distinguishes "site is unreachable" from None ("fetch succeeded but no text"),
        allowing the task layer to protect an already-classified article from being overwritten.
        """
        import httpx

        with patch(
            "recap.aiapi_helper.httpx.get",
            side_effect=httpx.ConnectError("[Errno 8] nodename nor servname provided, or not known"),
        ):
            with recap_app.app_context():
                from recap.aiapi_helper import fetch_article_content

                result = fetch_article_content("https://cq2.co/blog/the-best-way-to-have-complex-discussions")

        assert result is False

    @patch("recap.aiapi_helper._HAS_READABILITY", True)
    def test_returns_false_for_timeout(self, recap_app):
        """TimeoutException returns False (site treated as unreachable)."""
        import httpx

        with patch("recap.aiapi_helper.httpx.get", side_effect=httpx.TimeoutException("timed out")):
            with recap_app.app_context():
                from recap.aiapi_helper import fetch_article_content

                result = fetch_article_content("https://example.com/slow")

        assert result is False

    @patch("recap.aiapi_helper._HAS_READABILITY", True)
    def test_returns_false_for_http_status_error(self, recap_app):
        """Non-403 HTTPStatusError (e.g. 404, 5xx) returns False (page gone / server error)."""
        import httpx

        mock_response = MagicMock()
        req = httpx.Request("GET", "https://example.com/gone")
        resp = httpx.Response(404, request=req)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Not Found", request=req, response=resp)

        with patch("recap.aiapi_helper.httpx.get", return_value=mock_response):
            with recap_app.app_context():
                from recap.aiapi_helper import fetch_article_content

                result = fetch_article_content("https://example.com/gone")

        assert result is False

    @patch("recap.aiapi_helper._HAS_READABILITY", True)
    def test_returns_site_blocked_for_403_modeling_medium_bot_block(self, recap_app):
        """A 403 response returns SITE_BLOCKED (not False), modelling Medium's bot detection.

        SITE_BLOCKED is a falsy sentinel distinct from False ("site down"), so the task
        layer can classify the article from its URL while marking the title as blocked.
        """
        import httpx

        mock_response = MagicMock()
        req = httpx.Request(
            "GET",
            "https://kaustavmukherjee-66179.medium.com/improve-retrieval-of-documents-from-vectordb-using-maximum-marginal-relevance-mmr-for-balancing-f6ae56fb9512",
        )
        resp = httpx.Response(403, request=req)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Forbidden", request=req, response=resp)

        with patch("recap.aiapi_helper.httpx.get", return_value=mock_response):
            with recap_app.app_context():
                from recap.aiapi_helper import SITE_BLOCKED, fetch_article_content

                result = fetch_article_content(
                    "https://kaustavmukherjee-66179.medium.com/improve-retrieval-of-documents-from-vectordb-using-maximum-marginal-relevance-mmr-for-balancing-f6ae56fb9512"
                )

        assert result is SITE_BLOCKED
        assert not result  # falsy — won't be sent as article content to the AI

    @patch("recap.aiapi_helper._HAS_READABILITY", True)
    def test_site_blocked_is_distinct_from_site_down(self, recap_app):
        """SITE_BLOCKED and False are different objects so identity checks are unambiguous."""
        import httpx

        req = httpx.Request("GET", "https://example.com")
        blocked_resp = httpx.Response(403, request=req)
        mock_blocked = MagicMock()
        mock_blocked.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=req, response=blocked_resp
        )

        with patch("recap.aiapi_helper.httpx.get", return_value=mock_blocked):
            with recap_app.app_context():
                from recap.aiapi_helper import SITE_BLOCKED, fetch_article_content

                blocked_result = fetch_article_content("https://example.com")

        with patch("recap.aiapi_helper.httpx.get", side_effect=httpx.ConnectError("DNS fail")):
            with recap_app.app_context():
                from recap.aiapi_helper import fetch_article_content

                down_result = fetch_article_content("https://example.com")

        assert blocked_result is SITE_BLOCKED
        assert down_result is False
        assert blocked_result is not down_result

    @patch("recap.aiapi_helper._HAS_READABILITY", True)
    @patch("recap.aiapi_helper.lxml_html")
    @patch("recap.aiapi_helper.Document")
    @patch("recap.aiapi_helper.httpx")
    def test_returns_none_when_extraction_empty(self, mock_httpx, mock_document, mock_lxml_html, recap_app):
        """When readability returns empty summary, return None."""
        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        mock_doc_instance = MagicMock()
        mock_doc_instance.summary.return_value = "   \n  "
        mock_document.return_value = mock_doc_instance

        with recap_app.app_context():
            from recap.aiapi_helper import fetch_article_content

            result = fetch_article_content("https://example.com/article")
        assert result is None


@pytest.mark.unit
@pytest.mark.recap
class TestClassifyUrlWithContent:
    """Tests for ClassifyUrl when content fetch is used."""

    @patch("recap.aiapi_helper.httpx.post")
    @patch("recap.aiapi_helper.fetch_article_content")
    def test_classify_url_includes_content_when_fetch_returns_text(self, mock_fetch, mock_post, recap_app):
        """When fetch_article_content returns text, POST data includes 'content'."""
        mock_fetch.return_value = "Extracted article text here."
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "author": "Test",
            "blog_title": "Title",
            "category": "AI",
            "summary": "Summary",
            "key_topics": [],
            "sub_categories": [],
            "url": "https://example.com",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            AiApiHelper.ClassifyUrl("https://example.com/article", "ref-1")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["timeout"] >= 60
        data = call_kwargs["data"]
        assert "content" in data
        assert data["content"] == "Extracted article text here."

    @patch("recap.aiapi_helper.httpx.post")
    @patch("recap.aiapi_helper.fetch_article_content")
    def test_classify_url_omits_content_when_fetch_returns_none(self, mock_fetch, mock_post, recap_app):
        """When fetch_article_content returns None, POST data does not include content."""
        mock_fetch.return_value = None
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "author": "Unknown",
            "blog_title": "Unknown",
            "category": "Other",
            "summary": "No content",
            "key_topics": [],
            "sub_categories": [],
            "url": "https://example.com",
        }
        mock_post.return_value = mock_response

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            AiApiHelper.ClassifyUrl("https://example.com/article", "ref-1")

        mock_post.assert_called_once()
        data = mock_post.call_args[1]["data"]
        assert "content" not in data


@pytest.mark.unit
@pytest.mark.recap
class TestPerformTask:
    """Tests for AiApiHelper.PerformTask."""

    @patch("recap.aiapi_helper.httpx.post")
    def test_perform_task_returns_json_on_success(self, mock_post, recap_app):
        """PerformTask returns parsed JSON from the API response."""
        mock_response = mock_post.return_value
        mock_response.json.return_value = {"result": "done", "ref_key": "ref-abc"}

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.PerformTask(
                context="Some context",
                prompt="Summarise this",
                format="json",
                ref_key="ref-abc",
            )

        assert result == {"result": "done", "ref_key": "ref-abc"}
        mock_post.assert_called_once()

    @patch("recap.aiapi_helper.httpx.post")
    def test_perform_task_sends_correct_fields(self, mock_post, recap_app):
        """PerformTask posts context, format, secret, and ref_key to the API."""
        mock_response = mock_post.return_value
        mock_response.json.return_value = {}

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            AiApiHelper.PerformTask(
                context="ctx",
                prompt="do something",
                format="plain",
                ref_key="key-1",
            )

        call_kwargs = mock_post.call_args[1]
        data = call_kwargs["data"]
        assert data["context"] == "ctx"
        assert data["format"] == "plain"
        assert data["ref_key"] == "key-1"
        assert "secret" in data

    @patch("recap.aiapi_helper.httpx.post")
    def test_perform_task_returns_empty_dict_on_http_error(self, mock_post, recap_app):
        """PerformTask returns {} and does not raise when the HTTP call fails."""
        import httpx

        mock_post.side_effect = httpx.RequestError("connection refused")

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.PerformTask(
                context="ctx",
                prompt="p",
                format="f",
                ref_key="k",
            )

        assert result == {}

    @patch("recap.aiapi_helper.httpx.post")
    def test_perform_task_returns_empty_dict_on_json_decode_error(self, mock_post, recap_app):
        """PerformTask returns {} when the response body is not valid JSON."""
        mock_response = mock_post.return_value
        mock_response.json.side_effect = ValueError("invalid JSON")

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.PerformTask(context="ctx", prompt="p", format="f", ref_key="k")

        assert result == {}

    @patch("recap.aiapi_helper.httpx.post")
    def test_perform_task_returns_empty_dict_on_connection_error(self, mock_post, recap_app):
        """PerformTask returns {} on ConnectionError."""
        mock_post.side_effect = ConnectionError("refused")

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.PerformTask(context="ctx", prompt="p", format="f", ref_key="k")

        assert result == {}

    @patch("recap.aiapi_helper.httpx.post")
    def test_perform_task_returns_empty_dict_on_unexpected_error(self, mock_post, recap_app):
        """PerformTask returns {} on any unexpected exception."""
        mock_post.side_effect = RuntimeError("unexpected")

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.PerformTask(context="ctx", prompt="p", format="f", ref_key="k")

        assert result == {}


@pytest.mark.unit
@pytest.mark.recap
class TestFetchArticleContentEdgeCases:
    """Additional edge-case coverage for fetch_article_content."""

    @patch("recap.aiapi_helper._HAS_READABILITY", False)
    def test_returns_none_when_readability_not_installed(self, recap_app):
        """When readability is unavailable, fetch_article_content immediately returns None."""
        with recap_app.app_context():
            from recap.aiapi_helper import fetch_article_content

            result = fetch_article_content("https://example.com/article")
        assert result is None

    @patch("recap.aiapi_helper._HAS_READABILITY", True)
    @patch("recap.aiapi_helper.lxml_html")
    @patch("recap.aiapi_helper.Document")
    @patch("recap.aiapi_helper.httpx")
    def test_returns_none_when_text_empty_after_whitespace_strip(
        self, mock_httpx, mock_document, mock_lxml_html, recap_app
    ):
        """Returns None when extracted text is only whitespace (empty after strip)."""
        mock_response = MagicMock()
        mock_response.text = "<html/>"
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        mock_doc_instance = MagicMock()
        mock_doc_instance.summary.return_value = "<p>   </p>"
        mock_document.return_value = mock_doc_instance

        mock_tree = MagicMock()
        mock_tree.text_content.return_value = "   \t\n  "
        mock_lxml_html.fromstring.return_value = mock_tree

        with recap_app.app_context():
            from recap.aiapi_helper import fetch_article_content

            result = fetch_article_content("https://example.com/article")
        assert result is None


@pytest.mark.unit
@pytest.mark.recap
class TestClassifyUrlErrorHandlers:
    """Tests for ClassifyUrl HTTP error handling paths."""

    @patch("recap.aiapi_helper.fetch_article_content", return_value=None)
    @patch("recap.aiapi_helper.httpx.post")
    def test_returns_empty_dict_on_http_error(self, mock_post, mock_fetch, recap_app):
        """ClassifyUrl returns {} when httpx raises an HTTPError."""
        import httpx as _httpx

        mock_post.side_effect = _httpx.HTTPError("bad response")

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.ClassifyUrl("https://example.com", "ref-1")

        assert result == {}

    @patch("recap.aiapi_helper.fetch_article_content", return_value=None)
    @patch("recap.aiapi_helper.httpx.post")
    def test_returns_empty_dict_on_connection_error(self, mock_post, mock_fetch, recap_app):
        """ClassifyUrl returns {} on ConnectionError."""
        mock_post.side_effect = ConnectionError("refused")

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.ClassifyUrl("https://example.com", "ref-1")

        assert result == {}

    @patch("recap.aiapi_helper.fetch_article_content", return_value=None)
    @patch("recap.aiapi_helper.httpx.post")
    def test_returns_empty_dict_on_value_error(self, mock_post, mock_fetch, recap_app):
        """ClassifyUrl returns {} when JSON decoding fails."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("bad json")
        mock_post.return_value = mock_response

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.ClassifyUrl("https://example.com", "ref-1")

        assert result == {}

    @patch("recap.aiapi_helper.fetch_article_content", return_value=None)
    @patch("recap.aiapi_helper.httpx.post")
    def test_returns_empty_dict_on_unexpected_exception(self, mock_post, mock_fetch, recap_app):
        """ClassifyUrl returns {} on any unexpected exception."""
        mock_post.side_effect = RuntimeError("unexpected")

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.ClassifyUrl("https://example.com", "ref-1")

        assert result == {}


@pytest.mark.unit
@pytest.mark.recap
class TestClassifyUrlSiteDown:
    """Tests that ClassifyUrl propagates site_down=True when fetch_article_content returns False.

    False (vs None) means the site was unreachable (ConnectError, Timeout, HTTP error),
    which is distinct from the site being up but content being un-extractable.
    """

    _AI_RESULT = {
        "author": "Unknown",
        "blog_title": "Unknown",
        "category": "Technology",
        "summary": "Could not fetch content.",
        "key_topics": [],
        "sub_categories": [],
        "url": "https://cq2.co/blog/the-best-way-to-have-complex-discussions",
    }

    @patch("recap.aiapi_helper.httpx.post")
    @patch("recap.aiapi_helper.fetch_article_content", return_value=False)
    def test_sets_site_down_true_when_fetch_returns_false(self, mock_fetch, mock_post, recap_app):
        """When fetch_article_content returns False (site unreachable), result includes site_down=True."""
        mock_post.return_value.json.return_value = dict(self._AI_RESULT)

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.ClassifyUrl("https://cq2.co/blog/the-best-way-to-have-complex-discussions", "ref-1")

        assert result.get("site_down") is True

    @patch("recap.aiapi_helper.httpx.post")
    @patch("recap.aiapi_helper.fetch_article_content", return_value=False)
    def test_still_calls_ai_api_when_site_down(self, mock_fetch, mock_post, recap_app):
        """Even when site is down, ClassifyUrl still calls the AI API (URL-only prompt for new articles)."""
        mock_post.return_value.json.return_value = dict(self._AI_RESULT)

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            AiApiHelper.ClassifyUrl("https://cq2.co/blog/the-best-way-to-have-complex-discussions", "ref-1")

        mock_post.assert_called_once()
        data = mock_post.call_args[1]["data"]
        assert "content" not in data  # no content sent because fetch failed

    @patch("recap.aiapi_helper.httpx.post")
    @patch("recap.aiapi_helper.fetch_article_content", return_value=None)
    def test_does_not_set_site_down_when_fetch_returns_none(self, mock_fetch, mock_post, recap_app):
        """When fetch returns None (site up but no text), site_down is NOT set."""
        mock_post.return_value.json.return_value = dict(self._AI_RESULT)

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.ClassifyUrl("https://example.com", "ref-1")

        assert "site_down" not in result

    @patch("recap.aiapi_helper.httpx.post")
    @patch("recap.aiapi_helper.fetch_article_content", return_value="Full article text here.")
    def test_does_not_set_site_down_when_fetch_returns_text(self, mock_fetch, mock_post, recap_app):
        """When fetch returns text (site up), site_down is NOT set."""
        mock_post.return_value.json.return_value = dict(self._AI_RESULT)

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper

            result = AiApiHelper.ClassifyUrl("https://example.com", "ref-1")

        assert "site_down" not in result

    @patch("recap.aiapi_helper.httpx.post")
    def test_sets_site_blocked_true_when_fetch_returns_site_blocked(self, mock_post, recap_app):
        """When fetch returns SITE_BLOCKED (403), result includes site_blocked=True but NOT site_down."""
        mock_post.return_value.json.return_value = dict(self._AI_RESULT)

        with recap_app.app_context():
            from unittest.mock import patch as _patch

            from recap.aiapi_helper import SITE_BLOCKED, AiApiHelper

            with _patch("recap.aiapi_helper.fetch_article_content", return_value=SITE_BLOCKED):
                result = AiApiHelper.ClassifyUrl(
                    "https://kaustavmukherjee-66179.medium.com/improve-retrieval-of-documents-from-vectordb-using-maximum-marginal-relevance-mmr-for-balancing-f6ae56fb9512",
                    "ref-1",
                )

        assert result.get("site_blocked") is True
        assert "site_down" not in result

    @patch("recap.aiapi_helper.httpx.post")
    def test_blocked_content_not_sent_to_ai_api(self, mock_post, recap_app):
        """When fetch returns SITE_BLOCKED, the sentinel is NOT forwarded as article content."""
        mock_post.return_value.json.return_value = dict(self._AI_RESULT)

        with recap_app.app_context():
            from unittest.mock import patch as _patch

            from recap.aiapi_helper import SITE_BLOCKED, AiApiHelper

            with _patch("recap.aiapi_helper.fetch_article_content", return_value=SITE_BLOCKED):
                AiApiHelper.ClassifyUrl("https://medium.com/some-article", "ref-1")

        data = mock_post.call_args[1]["data"]
        assert "content" not in data
