"""Unit tests for AiApiHelper and fetch_article_content (Step 3 content fetch)."""
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit
@pytest.mark.recap
class TestFetchArticleContent:
    """Tests for fetch_article_content helper."""

    @patch('recap.aiapi_helper._HAS_READABILITY', True)
    @patch('recap.aiapi_helper.lxml_html')
    @patch('recap.aiapi_helper.Document')
    @patch('recap.aiapi_helper.httpx')
    def test_returns_extracted_text_when_fetch_succeeds(self, mock_httpx, mock_document, mock_lxml_html, recap_app):
        """When GET and readability succeed, return extracted text (truncated to max_chars)."""
        mock_response = MagicMock()
        mock_response.text = '<html/>'
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        mock_doc_instance = MagicMock()
        mock_doc_instance.summary.return_value = '<p>Hello world. ' + 'x' * 20000 + '</p>'
        mock_document.return_value = mock_doc_instance

        mock_tree = MagicMock()
        mock_tree.text_content.return_value = 'Hello world. ' + 'x' * 20000
        mock_lxml_html.fromstring.return_value = mock_tree

        with recap_app.app_context():
            from recap.aiapi_helper import fetch_article_content
            result = fetch_article_content('https://example.com/article', max_chars=12000)
        assert result is not None
        assert 'Hello world' in result
        assert len(result) <= 12000

    @patch('recap.aiapi_helper._HAS_READABILITY', True)
    @patch('recap.aiapi_helper.httpx')
    def test_returns_none_when_http_fails(self, mock_httpx, recap_app):
        """When httpx.get raises, return None."""
        import httpx
        mock_httpx.get.side_effect = httpx.RequestError('connection failed')

        with recap_app.app_context():
            from recap.aiapi_helper import fetch_article_content
            result = fetch_article_content('https://example.com/article')
        assert result is None

    @patch('recap.aiapi_helper._HAS_READABILITY', True)
    @patch('recap.aiapi_helper.lxml_html')
    @patch('recap.aiapi_helper.Document')
    @patch('recap.aiapi_helper.httpx')
    def test_returns_none_when_extraction_empty(self, mock_httpx, mock_document, mock_lxml_html, recap_app):
        """When readability returns empty summary, return None."""
        mock_response = MagicMock()
        mock_response.text = '<html></html>'
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        mock_doc_instance = MagicMock()
        mock_doc_instance.summary.return_value = '   \n  '
        mock_document.return_value = mock_doc_instance

        with recap_app.app_context():
            from recap.aiapi_helper import fetch_article_content
            result = fetch_article_content('https://example.com/article')
        assert result is None


@pytest.mark.unit
@pytest.mark.recap
class TestClassifyUrlWithContent:
    """Tests for ClassifyUrl when content fetch is used."""

    @patch('recap.aiapi_helper.httpx.post')
    @patch('recap.aiapi_helper.fetch_article_content')
    def test_classify_url_includes_content_when_fetch_returns_text(
        self, mock_fetch, mock_post, recap_app
    ):
        """When fetch_article_content returns text, POST data includes 'content'."""
        mock_fetch.return_value = 'Extracted article text here.'
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'author': 'Test',
            'blog_title': 'Title',
            'category': 'AI',
            'summary': 'Summary',
            'key_topics': [],
            'sub_categories': [],
            'url': 'https://example.com'
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper
            AiApiHelper.ClassifyUrl('https://example.com/article', 'ref-1')

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['timeout'] >= 60
        data = call_kwargs['data']
        assert 'content' in data
        assert data['content'] == 'Extracted article text here.'

    @patch('recap.aiapi_helper.httpx.post')
    @patch('recap.aiapi_helper.fetch_article_content')
    def test_classify_url_omits_content_when_fetch_returns_none(
        self, mock_fetch, mock_post, recap_app
    ):
        """When fetch_article_content returns None, POST data does not include content."""
        mock_fetch.return_value = None
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'author': 'Unknown',
            'blog_title': 'From URL only',
            'category': 'Other',
            'summary': 'No content',
            'key_topics': [],
            'sub_categories': [],
            'url': 'https://example.com'
        }
        mock_post.return_value = mock_response

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper
            AiApiHelper.ClassifyUrl('https://example.com/article', 'ref-1')

        mock_post.assert_called_once()
        data = mock_post.call_args[1]['data']
        assert 'content' not in data


@pytest.mark.unit
@pytest.mark.recap
class TestPerformTask:
    """Tests for AiApiHelper.PerformTask."""

    @patch('recap.aiapi_helper.httpx.post')
    def test_perform_task_returns_json_on_success(self, mock_post, recap_app):
        """PerformTask returns parsed JSON from the API response."""
        mock_response = mock_post.return_value
        mock_response.json.return_value = {'result': 'done', 'ref_key': 'ref-abc'}

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper
            result = AiApiHelper.PerformTask(
                context='Some context',
                prompt='Summarise this',
                format='json',
                ref_key='ref-abc',
            )

        assert result == {'result': 'done', 'ref_key': 'ref-abc'}
        mock_post.assert_called_once()

    @patch('recap.aiapi_helper.httpx.post')
    def test_perform_task_sends_correct_fields(self, mock_post, recap_app):
        """PerformTask posts context, format, secret, and ref_key to the API."""
        mock_response = mock_post.return_value
        mock_response.json.return_value = {}

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper
            AiApiHelper.PerformTask(
                context='ctx',
                prompt='do something',
                format='plain',
                ref_key='key-1',
            )

        call_kwargs = mock_post.call_args[1]
        data = call_kwargs['data']
        assert data['context'] == 'ctx'
        assert data['format'] == 'plain'
        assert data['ref_key'] == 'key-1'
        assert 'secret' in data

    @patch('recap.aiapi_helper.httpx.post')
    def test_perform_task_returns_empty_dict_on_http_error(self, mock_post, recap_app):
        """PerformTask returns {} and does not raise when the HTTP call fails."""
        import httpx
        mock_post.side_effect = httpx.RequestError('connection refused')

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper
            result = AiApiHelper.PerformTask(
                context='ctx',
                prompt='p',
                format='f',
                ref_key='k',
            )

        assert result == {}

    @patch('recap.aiapi_helper.httpx.post')
    def test_perform_task_returns_empty_dict_on_json_decode_error(self, mock_post, recap_app):
        """PerformTask returns {} when the response body is not valid JSON."""
        mock_response = mock_post.return_value
        mock_response.json.side_effect = ValueError('invalid JSON')

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper
            result = AiApiHelper.PerformTask(
                context='ctx', prompt='p', format='f', ref_key='k'
            )

        assert result == {}

    @patch('recap.aiapi_helper.httpx.post')
    def test_perform_task_returns_empty_dict_on_connection_error(self, mock_post, recap_app):
        """PerformTask returns {} on ConnectionError."""
        mock_post.side_effect = ConnectionError('refused')

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper
            result = AiApiHelper.PerformTask(
                context='ctx', prompt='p', format='f', ref_key='k'
            )

        assert result == {}

    @patch('recap.aiapi_helper.httpx.post')
    def test_perform_task_returns_empty_dict_on_unexpected_error(self, mock_post, recap_app):
        """PerformTask returns {} on any unexpected exception."""
        mock_post.side_effect = RuntimeError('unexpected')

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper
            result = AiApiHelper.PerformTask(
                context='ctx', prompt='p', format='f', ref_key='k'
            )

        assert result == {}


@pytest.mark.unit
@pytest.mark.recap
class TestFetchArticleContentEdgeCases:
    """Additional edge-case coverage for fetch_article_content."""

    @patch('recap.aiapi_helper._HAS_READABILITY', False)
    def test_returns_none_when_readability_not_installed(self, recap_app):
        """When readability is unavailable, fetch_article_content immediately returns None."""
        with recap_app.app_context():
            from recap.aiapi_helper import fetch_article_content
            result = fetch_article_content('https://example.com/article')
        assert result is None

    @patch('recap.aiapi_helper._HAS_READABILITY', True)
    @patch('recap.aiapi_helper.lxml_html')
    @patch('recap.aiapi_helper.Document')
    @patch('recap.aiapi_helper.httpx')
    def test_returns_none_when_text_empty_after_whitespace_strip(
        self, mock_httpx, mock_document, mock_lxml_html, recap_app
    ):
        """Returns None when extracted text is only whitespace (empty after strip)."""
        mock_response = MagicMock()
        mock_response.text = '<html/>'
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        mock_doc_instance = MagicMock()
        mock_doc_instance.summary.return_value = '<p>   </p>'
        mock_document.return_value = mock_doc_instance

        mock_tree = MagicMock()
        mock_tree.text_content.return_value = '   \t\n  '
        mock_lxml_html.fromstring.return_value = mock_tree

        with recap_app.app_context():
            from recap.aiapi_helper import fetch_article_content
            result = fetch_article_content('https://example.com/article')
        assert result is None


@pytest.mark.unit
@pytest.mark.recap
class TestClassifyUrlErrorHandlers:
    """Tests for ClassifyUrl HTTP error handling paths."""

    @patch('recap.aiapi_helper.fetch_article_content', return_value=None)
    @patch('recap.aiapi_helper.httpx.post')
    def test_returns_empty_dict_on_http_error(self, mock_post, mock_fetch, recap_app):
        """ClassifyUrl returns {} when httpx raises an HTTPError."""
        import httpx as _httpx
        mock_post.side_effect = _httpx.HTTPError('bad response')

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper
            result = AiApiHelper.ClassifyUrl('https://example.com', 'ref-1')

        assert result == {}

    @patch('recap.aiapi_helper.fetch_article_content', return_value=None)
    @patch('recap.aiapi_helper.httpx.post')
    def test_returns_empty_dict_on_connection_error(self, mock_post, mock_fetch, recap_app):
        """ClassifyUrl returns {} on ConnectionError."""
        mock_post.side_effect = ConnectionError('refused')

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper
            result = AiApiHelper.ClassifyUrl('https://example.com', 'ref-1')

        assert result == {}

    @patch('recap.aiapi_helper.fetch_article_content', return_value=None)
    @patch('recap.aiapi_helper.httpx.post')
    def test_returns_empty_dict_on_value_error(self, mock_post, mock_fetch, recap_app):
        """ClassifyUrl returns {} when JSON decoding fails."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError('bad json')
        mock_post.return_value = mock_response

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper
            result = AiApiHelper.ClassifyUrl('https://example.com', 'ref-1')

        assert result == {}

    @patch('recap.aiapi_helper.fetch_article_content', return_value=None)
    @patch('recap.aiapi_helper.httpx.post')
    def test_returns_empty_dict_on_unexpected_exception(self, mock_post, mock_fetch, recap_app):
        """ClassifyUrl returns {} on any unexpected exception."""
        mock_post.side_effect = RuntimeError('unexpected')

        with recap_app.app_context():
            from recap.aiapi_helper import AiApiHelper
            result = AiApiHelper.ClassifyUrl('https://example.com', 'ref-1')

        assert result == {}
