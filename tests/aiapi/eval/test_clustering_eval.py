"""
AI eval: cluster label quality with real OpenAI.

Scenario: testuser2 saved 5 articles about AI agent frameworks in a single week.
Before the n_clusters fix, _cluster_by_embedding created 5 single-article clusters.
_label_cluster then produced hallucinated labels like "Renewable Energy Innovations"
for the article "When to Use LangGraph" (documented in BUGS.md).

These tests call the real OpenAI API through the aiapi test client.

Run:
    pytest -m eval
    pytest tests/aiapi/eval/ -v

Requires: OPENAI_API_KEY environment variable
"""

import os

import pytest

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

pytestmark = [pytest.mark.eval, pytest.mark.aiapi]


@pytest.fixture
def eval_aiapi_client(aiapi_app):
    """aiapi test client with the real OpenAI key — eval tests only."""
    aiapi_app.config["AI_API_OPENAI"] = OPENAI_API_KEY
    return aiapi_app.test_client()


def _process_task(client, context, prompt, format_str):
    r = client.post(
        "/process_task",
        data={
            "context": context,
            "prompt": prompt,
            "format": format_str,
            "secret": "eval",
            "ref_key": "eval-test",
        },
    )
    assert r.status_code == 200, f"process_task returned {r.status_code}: {r.data}"
    return r.get_json()


@pytest.mark.skipif(not OPENAI_API_KEY, reason="OPENAI_API_KEY not set")
class TestClusterLabelQuality:
    """
    Eval: label quality for the AI agent framework cluster from testuser2's weekly digest.

    These tests assert semantic correctness of AI output — they are intentionally
    not mocked. Run them before changing LABEL_PROMPT or the clustering strategy.
    """

    def test_single_langgraph_title_is_not_labelled_as_environment(self, eval_aiapi_client):
        """
        Regression: the exact scenario from BUGS.md.

        "When to Use LangGraph" was sent as a single-article cluster and the model
        returned "Renewable Energy Innovations". After the category-fallback fix this
        code path is rarely hit, but if the AI is called with a single title it must
        not hallucinate an unrelated environmental label.
        """
        from aiapi.agents.synthesis.nodes import LABEL_FORMAT, LABEL_PROMPT

        context = "- When to Use LangGraph"
        result = _process_task(eval_aiapi_client, context, LABEL_PROMPT, LABEL_FORMAT)
        label = (result or {}).get("label", "")

        bad_terms = {"renewable", "energy", "environment", "climate", "green", "solar", "ecological"}
        assert not any(
            t in label.lower() for t in bad_terms
        ), f"Model hallucinated an environmental label for a LangGraph article: {label!r}"

    def test_ai_agent_framework_articles_produce_ai_related_label(self, eval_aiapi_client):
        """
        The four AI agent-framework articles from testuser2's recent weekly digest
        should produce a label that references AI, agents, or frameworks — matching
        the production result "AI Agent Frameworks Comparison".
        """
        from aiapi.agents.synthesis.nodes import LABEL_FORMAT, LABEL_PROMPT

        context = "\n".join(
            [
                "- When to Use LangGraph",
                "- Comparing AI agent frameworks: CrewAI, LangGraph, and BeeAI",
                "- LangGraph vs CrewAI: A Comprehensive Comparison of AI Agentic Frameworks",
                "- Deploy AI Agent on Render with Auto-Scaling and Monitoring",
            ]
        )
        result = _process_task(eval_aiapi_client, context, LABEL_PROMPT, LABEL_FORMAT)
        label = (result or {}).get("label", "")

        ai_terms = {"ai", "agent", "langgraph", "llm", "framework", "crewai", "agentic", "workflow"}
        assert any(
            t in label.lower() for t in ai_terms
        ), f"Expected an AI/agent/framework label for these articles, got: {label!r}"

    def test_label_format_returns_valid_json_with_label_key(self, eval_aiapi_client):
        """Sanity check: LABEL_FORMAT produces a JSON object with a 'label' key."""
        from aiapi.agents.synthesis.nodes import LABEL_FORMAT, LABEL_PROMPT

        context = "- Vector Search Guide\n- HNSW Indexing in Postgres"
        result = _process_task(eval_aiapi_client, context, LABEL_PROMPT, LABEL_FORMAT)
        assert isinstance(result, dict), f"Expected dict response, got: {type(result)}"
        assert "label" in result, f"Missing 'label' key in response: {result}"
        assert isinstance(result["label"], str) and result["label"], "label must be a non-empty string"
