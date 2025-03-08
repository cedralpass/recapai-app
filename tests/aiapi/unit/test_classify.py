import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit
@pytest.mark.aiapi
class TestClassify:
    def test_unauthorized_access(self, aiapi_client):
        """Test that unauthorized requests are rejected."""
        print("\nTesting unauthorized access to classify endpoint")
        response = aiapi_client.post('/classify_url', data={
            'url': 'http://example.com', 
            'ref_key': 'test-ref-key'
        })
        print(f"Response status code: {response.status_code}")
        print(f"Response data: {response.data}")
        assert response.status_code == 401
       # assert b"Not Authorized" in response.data
    
    @patch('aiapi.classify.OpenAI')
    def test_classify_endpoint(self, mock_openai, aiapi_client):
        """Test the classification endpoint with mocked OpenAI."""
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = '{"category": "Technology"}'
        mock_openai.return_value.chat.completions.create.return_value = mock_completion
        
        response = aiapi_client.post('/classify_url', 
            data={
                'url': 'http://example.com',
                'secret': 'test-token'
            })
        
        print(f"Response status code: {response.status_code}")
        print(f"Response data: {response.data}")
        assert response.status_code == 200
        assert b'category' in response.data 