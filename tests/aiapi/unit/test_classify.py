import pytest
from unittest.mock import patch, MagicMock
import json

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
        mock_response = {
            "author": "Better Stack Community",
            "blog_title": "How to Start Logging with Flask",
            "category": "Software Architecture",
            "key_topics": [
                "Flask logging setup",
                "Importance of logging in applications",
                "Use of third-party logging tools"
            ],
            "sub_categories": [
                "Flask Framework",
                "Application Monitoring",
                "Debugging Techniques"
            ],
            "summary": "This blog post provides a comprehensive guide on implementing logging in Flask applications. It covers the basics of logging, setting up a simple logging configuration, and using third-party logging tools for better log management. The guide emphasizes the importance of logging for monitoring and debugging Flask applications and provides code examples to help developers get started.",
            "url": "https://betterstack.com/community/guides/logging/how-to-start-logging-with-flask/"
        }
        # Convert mock_response to a JSON string since that's what the API would return
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = MagicMock()
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_openai.return_value.chat.completions.create.return_value = mock_completion
        
        response = aiapi_client.post('/classify_url', 
            data={
                'url': 'https://betterstack.com/community/guides/logging/how-to-start-logging-with-flask/',
                'secret': 'test-token',
                'ref_key': '2'
            })
        
        print(f"Response status code: {response.status_code}")
        print(f"Response data: {response.data}")
        assert response.status_code == 200
        
        response_data = json.loads(response.data)
        assert response_data['category'] == 'Software Architecture'
        assert response_data['author'] == 'Better Stack Community'
        assert response_data['blog_title'] == 'How to Start Logging with Flask'
        assert len(response_data['key_topics']) == 3
        assert len(response_data['sub_categories']) == 3
        assert response_data['ref_key'] == '2' 