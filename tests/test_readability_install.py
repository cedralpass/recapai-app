"""
Test that readability-lxml and lxml (with required modules) are installed correctly.
Used to catch missing or broken deps (e.g. lxml 5.2+ without lxml_html_clean, or Alpine without libxml2-dev).

If these tests fail:
- Local: pip install -r requirements.txt (use lxml>=5.1.0,<5.2 so html.clean is built-in).
- Alpine Docker: ensure Dockerfile has libxml2-dev libxslt-dev gcc musl-dev before pip install.
"""
import pytest


def test_readability_and_lxml_import():
    """readability.Document and lxml.html must be importable for content extraction."""
    from readability import Document
    from lxml import html

    assert Document is not None
    assert html is not None


def test_readability_document_extracts_from_html():
    """Minimal extraction: Document(html).summary() works (ensures lxml.html.clean path is available)."""
    from readability import Document

    minimal_html = """
    <html><body>
    <article>
        <h1>Test Title</h1>
        <p>First paragraph. Second sentence.</p>
        <p>Another paragraph.</p>
    </article>
    </body></html>
    """
    doc = Document(minimal_html)
    summary = doc.summary()
    assert summary is not None
    assert "Test Title" in summary or "First paragraph" in summary or "Another" in summary
