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
