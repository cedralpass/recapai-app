import pytest
from unittest.mock import patch, MagicMock
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"

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

    # ------------------------------------------------------------------
    # Taxonomy / max_tokens regression tests
    # ------------------------------------------------------------------

    @patch('aiapi.task_processor.OpenAI')
    def test_max_tokens_is_1024_or_greater(self, mock_openai, aiapi_client):
        """Regression guard: OpenAI must be called with max_tokens >= 1024.

        Previously max_tokens=512 caused JSON truncation when processing
        taxonomies with 20+ categories, raising JSONDecodeError in production.
        """
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps({"result": "ok"})
        mock_openai.return_value.chat.completions.create.return_value = mock_completion

        aiapi_client.post('/process_task', data={
            'context': 'test context',
            'prompt': 'test prompt',
            'format': 'json',
            'secret': 'test-token',
            'ref_key': '1',
        })

        call_kwargs = mock_openai.return_value.chat.completions.create.call_args.kwargs
        assert call_kwargs['max_tokens'] >= 1024, (
            f"max_tokens={call_kwargs['max_tokens']} is too low — "
            "large taxonomy responses will be truncated and cause JSONDecodeError"
        )

    @patch('aiapi.task_processor.OpenAI')
    def test_truncated_json_from_openai_returns_500(self, mock_openai, aiapi_client):
        """Replicate the production bug: OpenAI returns JSON cut off mid-object.

        This is what happened in production when max_tokens=512 was hit on a
        21-category taxonomy.  The endpoint should not crash with an unhandled
        exception — it returns 500, which is caught by Flask's error handler.
        """
        # Simulate truncated JSON — exactly what OpenAI returned when it hit
        # the old 512-token limit mid-response.
        truncated = (
            '{\n    "description": "Categories were consolidated.",\n'
            '    "mappings": [\n'
            '        {"new_category": "Artificial Intelligence", "old_category": "Artificial Intelligence"},\n'
            '        {"new_category": "Business & Leadership", "old_category": "Business Strategy"'
            # deliberately cut off here — no closing brackets
        )
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = truncated
        mock_openai.return_value.chat.completions.create.return_value = mock_completion

        response = aiapi_client.post('/process_task', data={
            'context': 'test context',
            'prompt': 'test prompt',
            'format': 'json',
            'secret': 'test-token',
            'ref_key': '2',
        })

        assert response.status_code == 500, (
            "Truncated JSON from OpenAI should produce a 500 — "
            "add try/except around json.loads() in task_processor.py to handle this gracefully"
        )

    @patch('aiapi.task_processor.OpenAI')
    def test_large_taxonomy_21_categories_processes_successfully(self, mock_openai, aiapi_client):
        """Full 21-category response (mirrors the production payload) must parse correctly.

        Uses the fixture built from the actual production log to verify that
        a taxonomy of this size is handled end-to-end without truncation errors.
        """
        fixture_path = FIXTURES_DIR / "organize_taxonomy_large_response.json"
        full_response = json.loads(fixture_path.read_text())

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(full_response)
        mock_openai.return_value.chat.completions.create.return_value = mock_completion

        response = aiapi_client.post('/process_task', data={
            'context': (
                'I am using this taxonomy to categorize content: '
                'Artificial Intelligence, Business Strategy, Consumer Electronics, Cooking, '
                'Culinary Arts, Fitness & Health, Government Policy, Health & Wellness, '
                'Leadership, Outdoor Recreation, Product Management, Product Review, '
                'Recreational Fishing, Science & Technology, Software Architecture, '
                'Software Development, Sustainability and Environment, Travel & Adventure, '
                'Travel and Recreation, Web Design, Writing Techniques.'
            ),
            'prompt': (
                'Can you recommend a category list, consolidating similar categories? '
                'However, keep Artificial Intelligence and Software Architecture. '
                'Keep categories concise and understandable to a human reader.'
            ),
            'format': 'json',
            'secret': 'test-token',
            'ref_key': '2',
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'mappings' in data
        assert len(data['mappings']) == 21
        assert data['ref_key'] == '2'
        # Pinned categories must survive unchanged
        pinned = [m for m in data['mappings'] if m['old_category'] == m['new_category']
                  and m['new_category'] in ('Artificial Intelligence', 'Software Architecture')]
        assert len(pinned) == 2