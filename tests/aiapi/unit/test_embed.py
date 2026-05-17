"""Unit tests for aiapi POST /embed endpoint."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@pytest.mark.aiapi
class TestEmbedEndpoint:
    def test_returns_embedding_vector(self, aiapi_client):
        fake_vec = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=fake_vec)]

        with patch("aiapi.embeddings.OpenAI") as mock_openai:
            mock_openai.return_value.embeddings.create.return_value = mock_response
            response = aiapi_client.post("/embed", data={"text": "hello world", "secret": "abc123"})

        assert response.status_code == 200
        data = response.get_json()
        assert "embedding" in data
        assert len(data["embedding"]) == 1536

    def test_missing_text_returns_400(self, aiapi_client):
        response = aiapi_client.post("/embed", data={"text": "", "secret": "abc123"})
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_missing_secret_returns_401(self, aiapi_client):
        response = aiapi_client.post("/embed", data={"text": "hello"})
        assert response.status_code == 401

    def test_calls_correct_embedding_model(self, aiapi_client):
        fake_vec = [0.0] * 1536
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=fake_vec)]

        with patch("aiapi.embeddings.OpenAI") as mock_openai:
            mock_instance = mock_openai.return_value
            mock_instance.embeddings.create.return_value = mock_response
            aiapi_client.post("/embed", data={"text": "test input", "secret": "abc123"})

        call_kwargs = mock_instance.embeddings.create.call_args[1]
        assert call_kwargs["model"] == "text-embedding-3-small"
        assert call_kwargs["input"] == "test input"
