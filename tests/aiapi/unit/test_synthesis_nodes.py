"""Unit tests for the weekly synthesis agent nodes.

Each node is a pure function (state in → state out). AI calls are mocked so
these tests run without a live aiapi or OpenAI key.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from aiapi.agents.synthesis.nodes import (
    _build_cluster_context,
    _cluster_by_category,
    _cluster_by_embedding,
    _label_cluster,
    _render_plain_text,
    assess,
    gather,
    quality_check,
    synthesise,
)
from aiapi.agents.synthesis.state import SynthesisState

# ── Helpers ───────────────────────────────────────────────────────────────────

_WEEK_START = datetime(2026, 5, 19, 0, 0, tzinfo=timezone.utc)
_WEEK_END = datetime(2026, 5, 26, 0, 0, tzinfo=timezone.utc)


def _base_state(**overrides) -> SynthesisState:
    state: SynthesisState = {
        "user_id": 1,
        "user_email": "test@example.com",
        "user_name": "testuser",
        "week_start": _WEEK_START,
        "week_end": _WEEK_END,
        "articles": [],
        "clusters": [],
        "clustering_strategy": "category",
        "skip_reason": None,
        "retry_count": 0,
        "quality_verdict": "",
        "quality_notes": "",
        "digest_html": "",
        "digest_text": "",
        "sent": False,
        "sent_at": None,
        "send_email_flag": False,
        "run_id": None,
    }
    state.update(overrides)
    return state


def _make_article(id=1, title="Test Article", category="Technology", **kwargs):
    return {
        "id": id,
        "title": title,
        "summary": "A test article summary.",
        "category": category,
        "key_topics": ["topic1", "topic2"],
        "url_path": f"https://example.com/{id}",
        "is_read": False,
        "embedding": None,
        **kwargs,
    }


# ── assess node ───────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestAssessNode:
    def test_skip_when_fewer_than_three_articles(self):
        state = _base_state(articles=[_make_article(1), _make_article(2)])
        result = assess(state)
        assert result["skip_reason"] is not None
        assert "2" in result["skip_reason"]

    def test_skip_zero_articles(self):
        state = _base_state(articles=[])
        result = assess(state)
        assert result["skip_reason"] is not None

    def test_proceeds_with_three_or_more_articles(self):
        articles = [_make_article(i) for i in range(5)]
        state = _base_state(articles=articles)
        result = assess(state)
        assert result.get("skip_reason") is None
        assert result["clustering_strategy"] in ("category", "embedding")

    def test_category_strategy_when_no_embeddings(self):
        articles = [_make_article(i) for i in range(5)]
        state = _base_state(articles=articles)
        result = assess(state)
        assert result["clustering_strategy"] == "category"

    def test_embedding_strategy_when_mostly_embedded(self):
        articles = [_make_article(i, embedding=[0.1] * 1536) for i in range(5)]
        state = _base_state(articles=articles)
        result = assess(state)
        assert result["clustering_strategy"] == "embedding"

    def test_category_strategy_when_few_embeddings(self):
        # Only 1 of 5 has embedding — below 80% threshold
        articles = [_make_article(i) for i in range(4)]
        articles.append(_make_article(5, embedding=[0.1] * 1536))
        state = _base_state(articles=articles)
        result = assess(state)
        assert result["clustering_strategy"] == "category"


# ── _cluster_by_category ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestClusterByCategory:
    def test_groups_by_category(self):
        articles = [
            _make_article(1, category="AI"),
            _make_article(2, category="AI"),
            _make_article(3, category="Design"),
        ]
        clusters = _cluster_by_category(articles)
        labels = {c["label"] for c in clusters}
        assert labels == {"AI", "Design"}

    def test_article_counts_per_cluster(self):
        articles = [_make_article(i, category="AI") for i in range(3)]
        clusters = _cluster_by_category(articles)
        assert len(clusters) == 1
        assert len(clusters[0]["articles"]) == 3

    def test_narrative_initialised_empty(self):
        clusters = _cluster_by_category([_make_article(1)])
        assert clusters[0]["narrative"] == ""

    def test_missing_category_goes_to_uncategorised(self):
        article = _make_article(1, category="")
        clusters = _cluster_by_category([article])
        assert clusters[0]["label"] == "Uncategorised"


# ── _label_cluster ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestLabelCluster:
    def test_single_article_uses_category_fallback(self):
        """Regression: single-article clusters must not ask the AI to label — it hallucinates.
        'When to Use LangGraph' was labelled 'Renewable Energy Innovations' before this fix."""
        article = _make_article(1, title="When to Use LangGraph", category="AI Infrastructure & Deployment")
        label = _label_cluster([article])
        assert label == "AI Infrastructure & Deployment"

    def test_single_article_without_category_falls_to_mixed(self):
        """No category set — falls through to AI call, which we mock."""
        article = _make_article(1, title="When to Use LangGraph", category="")
        with patch("recap.aiapi_helper.AiApiHelper.PerformTask", return_value=None):
            label = _label_cluster([article])
        assert label == "Mixed Topics"

    def test_multi_article_cluster_calls_ai(self):
        articles = [_make_article(i, title=f"AI Article {i}") for i in range(3)]
        with patch("recap.aiapi_helper.AiApiHelper.PerformTask", return_value={"label": "AI Frameworks"}) as mock_task:
            label = _label_cluster(articles)
        mock_task.assert_called_once()
        assert label == "AI Frameworks"


# ── _cluster_by_embedding ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestClusterByEmbedding:
    """Verify the n_clusters fix: small article sets must not produce single-article clusters."""

    def _ai_articles(self, n):
        """n articles with embeddings clustered around [1, 0, 0, 0]."""
        return [_make_article(i, title=f"AI Article {i}", embedding=[1.0, 0.0, 0.0, 0.0]) for i in range(n)]

    def _other_articles(self, n, offset=10):
        """n articles with embeddings clustered around [0, 1, 0, 0]."""
        return [_make_article(offset + i, title=f"Other Article {i}", embedding=[0.0, 1.0, 0.0, 0.0]) for i in range(n)]

    def test_five_articles_produces_at_most_two_clusters(self):
        """Old formula: min(5, 5) = 5 single-article clusters. New formula: min(5, 5//2) = 2."""
        articles = self._ai_articles(3) + self._other_articles(2)
        with patch("recap.aiapi_helper.AiApiHelper.PerformTask", return_value={"label": "Theme"}):
            clusters = _cluster_by_embedding(articles)
        assert len(clusters) <= 2

    def test_no_single_article_clusters_for_five_articles(self):
        """Every cluster must have at least 2 articles when there are 5 inputs."""
        articles = self._ai_articles(3) + self._other_articles(2)
        with patch("recap.aiapi_helper.AiApiHelper.PerformTask", return_value={"label": "Theme"}):
            clusters = _cluster_by_embedding(articles)
        for c in clusters:
            assert len(c["articles"]) >= 2, f"Single-article cluster found: {c}"

    def test_ten_articles_produces_at_most_five_clusters(self):
        articles = self._ai_articles(6) + self._other_articles(4)
        with patch("recap.aiapi_helper.AiApiHelper.PerformTask", return_value={"label": "Theme"}):
            clusters = _cluster_by_embedding(articles)
        assert len(clusters) <= 5

    def test_falls_back_to_category_when_fewer_than_two_embedded(self):
        articles = [_make_article(1, category="AI", embedding=[1.0, 0.0])]
        clusters = _cluster_by_embedding(articles)
        assert clusters[0]["label"] == "AI"

    def test_unembedded_articles_appended_to_first_cluster(self):
        embedded = self._ai_articles(4)
        unembedded = [_make_article(99, title="No Embedding", category="Other", embedding=None)]
        with patch("recap.aiapi_helper.AiApiHelper.PerformTask", return_value={"label": "Theme"}):
            clusters = _cluster_by_embedding(embedded + unembedded)
        total_articles = sum(len(c["articles"]) for c in clusters)
        assert total_articles == 5


# ── _build_cluster_context ────────────────────────────────────────────────────


@pytest.mark.unit
class TestBuildClusterContext:
    def test_includes_label_and_title(self):
        cluster = {"label": "AI", "articles": [_make_article(1, title="My Article")], "narrative": ""}
        ctx = _build_cluster_context(cluster)
        assert "AI" in ctx
        assert "My Article" in ctx

    def test_includes_quality_notes_on_retry(self):
        cluster = {"label": "AI", "articles": [_make_article(1)], "narrative": ""}
        ctx = _build_cluster_context(cluster, quality_notes="Be more specific.")
        assert "Be more specific." in ctx

    def test_no_quality_notes_in_first_pass(self):
        cluster = {"label": "AI", "articles": [_make_article(1)], "narrative": ""}
        ctx = _build_cluster_context(cluster)
        assert "Improvement notes" not in ctx


# ── synthesise node ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSynthesiseNode:
    def test_writes_narrative_per_cluster(self):
        articles = [_make_article(i) for i in range(3)]
        clusters = _cluster_by_category(articles)
        state = _base_state(articles=articles, clusters=clusters)

        with patch("recap.aiapi_helper.AiApiHelper.PerformTask", return_value={"narrative": "Deep insight here."}):
            result = synthesise(state)

        assert result["clusters"][0]["narrative"] == "Deep insight here."

    def test_handles_empty_ai_response(self):
        articles = [_make_article(i) for i in range(3)]
        clusters = _cluster_by_category(articles)
        state = _base_state(articles=articles, clusters=clusters)

        with patch("recap.aiapi_helper.AiApiHelper.PerformTask", return_value={}):
            result = synthesise(state)

        assert result["clusters"][0]["narrative"] == ""


# ── quality_check node ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestQualityCheckNode:
    def test_approved_verdict_passes_through(self):
        state = _base_state(digest_text="Good digest content.", retry_count=0)

        with patch("recap.aiapi_helper.AiApiHelper.PerformTask", return_value={"verdict": "approved", "notes": ""}):
            result = quality_check(state)

        assert result["quality_verdict"] == "approved"
        assert result["retry_count"] == 1

    def test_retry_verdict_is_preserved(self):
        state = _base_state(digest_text="Thin content.", retry_count=0)

        with patch(
            "recap.aiapi_helper.AiApiHelper.PerformTask",
            return_value={"verdict": "retry", "notes": "Too vague."},
        ):
            result = quality_check(state)

        assert result["quality_verdict"] == "retry"
        assert result["quality_notes"] == "Too vague."

    def test_best_effort_at_retry_limit(self):
        state = _base_state(digest_text="anything", retry_count=2)
        result = quality_check(state)
        assert result["quality_verdict"] == "best_effort"

    def test_unknown_verdict_defaults_to_approved(self):
        state = _base_state(digest_text="content", retry_count=0)

        with patch("recap.aiapi_helper.AiApiHelper.PerformTask", return_value={"verdict": "maybe"}):
            result = quality_check(state)

        assert result["quality_verdict"] == "approved"

    def test_retry_count_increments(self):
        state = _base_state(digest_text="content", retry_count=0)

        with patch("recap.aiapi_helper.AiApiHelper.PerformTask", return_value={"verdict": "approved"}):
            result = quality_check(state)

        assert result["retry_count"] == 1


# ── _render_plain_text ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestRenderPlainText:
    def test_includes_header_and_article_count(self):
        clusters = [
            {"label": "AI", "articles": [_make_article(1, title="Article One")], "narrative": "A great insight."}
        ]
        text = _render_plain_text("alice", _WEEK_START, clusters, 1)
        assert "alice" in text
        assert "1 article" in text
        assert "Article One" in text

    def test_includes_narratives(self):
        clusters = [{"label": "AI", "articles": [_make_article(1)], "narrative": "Key narrative text."}]
        text = _render_plain_text("bob", _WEEK_START, clusters, 1)
        assert "Key narrative text." in text

    def test_includes_footer(self):
        text = _render_plain_text("carol", _WEEK_START, [], 0)
        assert "Recap" in text


# ── graph routing ─────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGraphRouting:
    def test_route_after_gather_no_articles(self):
        from langgraph.graph import END

        from aiapi.agents.synthesis.graph import _route_after_gather

        state = _base_state(articles=[])
        assert _route_after_gather(state) == END

    def test_route_after_gather_has_articles(self):
        from aiapi.agents.synthesis.graph import _route_after_gather

        state = _base_state(articles=[_make_article(1)])
        assert _route_after_gather(state) == "assess"

    def test_route_after_assess_skip(self):
        from langgraph.graph import END

        from aiapi.agents.synthesis.graph import _route_after_assess

        state = _base_state(skip_reason="Only 1 article.")
        assert _route_after_assess(state) == END

    def test_route_after_assess_proceed(self):
        from aiapi.agents.synthesis.graph import _route_after_assess

        state = _base_state(skip_reason=None)
        assert _route_after_assess(state) == "cluster"

    def test_route_after_quality_approved(self):
        from aiapi.agents.synthesis.graph import _route_after_quality

        assert _route_after_quality(_base_state(quality_verdict="approved")) == "send_email"

    def test_route_after_quality_best_effort(self):
        from aiapi.agents.synthesis.graph import _route_after_quality

        assert _route_after_quality(_base_state(quality_verdict="best_effort")) == "send_email"

    def test_route_after_quality_retry(self):
        from aiapi.agents.synthesis.graph import _route_after_quality

        assert _route_after_quality(_base_state(quality_verdict="retry")) == "synthesise"

    def test_graph_compiles(self):
        from aiapi.agents.synthesis.graph import build_synthesis_graph

        graph = build_synthesis_graph()
        assert graph is not None


# ── send_email_node ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSendEmailNode:
    def test_no_email_sent_when_flag_false(self):
        from aiapi.agents.synthesis.nodes import send_email_node

        state = _base_state(
            digest_html="<p>digest</p>",
            digest_text="digest",
            send_email_flag=False,
        )
        with patch("recap.email.send_email") as mock_send:
            result = send_email_node(state)

        mock_send.assert_not_called()
        assert result["sent"] is False
        assert result["sent_at"] is not None

    def test_email_sent_when_flag_true(self):
        from aiapi.agents.synthesis.nodes import send_email_node

        state = _base_state(
            digest_html="<p>digest</p>",
            digest_text="digest",
            user_email="test@example.com",
            send_email_flag=True,
        )
        with (
            patch("recap.email.send_email") as mock_send,
            patch("recap.config.Config.MAIL_USERNAME", "noreply@recap.app"),
        ):
            result = send_email_node(state)

        mock_send.assert_called_once()
        assert result["sent"] is True


# ── gather node (with DB) ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestGatherNode:
    def test_gather_returns_articles_in_date_range(self, seeded_user, recap_app):
        with recap_app.app_context():
            # seeded articles have created dates in April 2026 — use a wide window
            from datetime import timedelta

            week_end = datetime(2026, 5, 1, tzinfo=timezone.utc)
            week_start = week_end - timedelta(days=400)
            state = _base_state(user_id=seeded_user.id, week_start=week_start, week_end=week_end)
            result = gather(state)
            assert len(result["articles"]) > 0

    def test_gather_returns_empty_for_future_window(self, seeded_user, recap_app):
        with recap_app.app_context():
            week_start = datetime(2030, 1, 1, tzinfo=timezone.utc)
            week_end = datetime(2030, 1, 7, tzinfo=timezone.utc)
            state = _base_state(user_id=seeded_user.id, week_start=week_start, week_end=week_end)
            result = gather(state)
            assert result["articles"] == []

    def test_gather_article_data_shape(self, seeded_user, recap_app):
        with recap_app.app_context():
            from datetime import timedelta

            week_end = datetime(2026, 5, 1, tzinfo=timezone.utc)
            week_start = week_end - timedelta(days=400)
            state = _base_state(user_id=seeded_user.id, week_start=week_start, week_end=week_end)
            result = gather(state)
            article = result["articles"][0]
            for key in ("id", "title", "summary", "category", "key_topics", "url_path", "is_read"):
                assert key in article
