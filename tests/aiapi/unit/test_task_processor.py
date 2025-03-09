import pytest
from unittest.mock import patch, MagicMock
import json

@pytest.mark.unit
@pytest.mark.aiapi
class TestTaskProcessor:
    def test_unauthorized_access(self, aiapi_client):
        """Test that unauthorized requests are rejected."""
        print("\nTesting unauthorized access to process_task endpoint")
        response = aiapi_client.post('/process_task', data={
            'context': 'test context',
            'prompt': 'test-prompt',
            'format': 'test-format',
            'ref_key': '2'
        })
        print(f"Response status code: {response.status_code}")
        print(f"Response data: {response.data}")
        assert response.status_code == 401

    @patch('aiapi.task_processor.OpenAI')
    def test_missing_required_fields(self, mock_openai, aiapi_client):
        """Test handling of missing required fields."""
        print("\nTesting missing required fields")
        
        # Set up mock OpenAI response
        mock_completion = MagicMock()
        mock_response = {
            "error": "Missing prompt"
        }
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = MagicMock()
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_openai.return_value.chat.completions.create.return_value = mock_completion
        
        response = aiapi_client.post('/process_task', data={
            'secret': 'test-token'
            # Missing context, prompt, and format
        })
        print(f"Response status code: {response.status_code}")
        print(f"Response data: {response.data}")
        assert response.status_code == 400
        assert json.loads(response.data)["error"] == "Missing prompt"
     

    @patch('aiapi.task_processor.OpenAI')
    def test_process_task_endpoint(self, mock_openai, aiapi_client):
        """Test the task processing endpoint with mocked OpenAI."""
        mock_completion = MagicMock()
        mock_response = {
            "result": "Task completed successfully",
            "details": "Processed the task as requested",
            "status": "success"
        }
        
        # Set up mock OpenAI response
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = MagicMock()
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_openai.return_value.chat.completions.create.return_value = mock_completion
        
        # Test data including prompt history
        prompt_history = [
            {"prompt": "previous question", "response": "previous answer"}
        ]
        
        response = aiapi_client.post('/process_task', data={
            'context': 'This is the context for processing',
            'prompt': 'Please process this task',
            'format': 'JSON format instructions',
            'secret': 'test-token',
            'ref_key': 'test-123',
            'prompt_history': json.dumps(prompt_history)
        })
        
        print(f"Response status code: {response.status_code}")
        print(f"Response data: {response.data}")
        assert response.status_code == 200
        
        response_data = json.loads(response.data)
        assert response_data['result'] == 'Task completed successfully'
        assert response_data['status'] == 'success'
        assert response_data['ref_key'] == 'test-123'

    def test_build_prompt_basic(self, aiapi_client):
        """Test build_prompt function with basic inputs."""
        from aiapi.task_processor import build_prompt
        
        with aiapi_client.application.app_context():
            context = "System context"
            prompt = "User prompt"
            
            result = build_prompt(context, prompt)
            
            assert len(result) == 2
            assert result[0]['role'] == 'system'
            assert result[0]['content'] == context
            assert result[1]['role'] == 'user'
            assert result[1]['content'] == prompt

    def test_build_prompt_with_format(self, aiapi_client):
        """Test build_prompt function with format instructions."""
        from aiapi.task_processor import build_prompt
        
        with aiapi_client.application.app_context():
            context = "System context"
            prompt = "User prompt"
            format_instructions = "Format instructions"
            
            result = build_prompt(context, prompt, format_instructions)
            
            assert len(result) == 3
            assert result[0]['role'] == 'system'
            assert result[0]['content'] == context
            assert result[1]['role'] == 'user'
            assert result[1]['content'] == prompt
            assert result[2]['role'] == 'system'
            assert result[2]['content'] == format_instructions

    def test_build_prompt_with_history(self, aiapi_client):
        """Test build_prompt function with prompt history."""
        from aiapi.task_processor import build_prompt
        
        with aiapi_client.application.app_context():
            context = "System context"
            prompt = "User prompt"
            prompt_history = [
                {"prompt": "previous question", "response": "previous answer"},
                {"prompt": "older question", "response": "older answer"}
            ]
            
            result = build_prompt(context, prompt, prompt_history=prompt_history)
            
            assert len(result) == 6  # 1 system + 4 history (2 pairs) + 1 final prompt
            assert result[0]['role'] == 'system'
            assert result[0]['content'] == context
            assert result[1]['role'] == 'user'
            assert result[1]['content'] == prompt
            assert result[2]['role'] == 'user'
            assert result[2]['content'] == "previous question"
            assert result[3]['role'] == 'system'
            assert result[3]['content'] == "previous answer"
            assert result[4]['role'] == 'user'
            assert result[4]['content'] == "older question"
            assert result[5]['role'] == 'system'
            assert result[5]['content'] == 'older answer'

    @patch('aiapi.task_processor.OpenAI')
    def test_process_task_no_choices(self, mock_openai, aiapi_client):
        """Test handling when OpenAI returns no choices."""
        # Set up mock OpenAI response with no choices
        mock_completion = MagicMock()
        mock_completion.choices = []  # Empty choices list
        mock_completion.model = "gpt-4"
        mock_completion.usage = "test usage"
        mock_openai.return_value.chat.completions.create.return_value = mock_completion
        
        response = aiapi_client.post('/process_task', data={
            'context': 'This is the context',
            'prompt': 'Please process this task',
            'format': 'JSON format',
            'secret': 'test-token',
            'ref_key': 'test-123'
        })
        
        print(f"Response status code: {response.status_code}")
        print(f"Response data: {response.data}")
        
        # The endpoint should return an error response
        assert response.status_code == 200  # The endpoint still returns 200
        response_data = json.loads(response.data)
        assert 'error' in response_data
        assert response_data['error'] == 'No response from OpenAI'

    @patch('aiapi.task_processor.OpenAI')
    def test_process_task_missing_ref_key(self, mock_openai, aiapi_client):
        """Test handling when ref_key is missing."""
        mock_completion = MagicMock()
        mock_response = {
            "result": "Task completed successfully",
            "status": "success"
        }
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = MagicMock()
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_openai.return_value.chat.completions.create.return_value = mock_completion
        
        response = aiapi_client.post('/process_task', data={
            'context': 'This is the context',
            'prompt': 'Please process this task',
            'format': 'JSON format',
            'secret': 'test-token'
            # Missing ref_key
        })
        
        print(f"Response status code: {response.status_code}")
        print(f"Response data: {response.data}")
        assert response.status_code == 200  # Should still return success
        response_data = json.loads(response.data)
        assert 'ref_key' not in response_data  # Should not have ref_key in response