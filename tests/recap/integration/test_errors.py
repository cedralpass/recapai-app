"""Integration tests for recap/errors — 404 and 500 error handlers."""
import pytest


@pytest.mark.integration
@pytest.mark.recap
class TestErrorHandlers:
    def test_404_returns_correct_status(self, recap_client):
        """A request to a nonexistent URL returns HTTP 404."""
        response = recap_client.get('/this/path/does/not/exist/xyz123')
        assert response.status_code == 404

    def test_404_renders_html_response(self, recap_client):
        """The 404 response body is HTML (not a bare Flask error page)."""
        response = recap_client.get('/no/such/page')
        assert response.status_code == 404
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data

    def test_internal_error_handler_returns_500(self, recap_app):
        """internal_error handler returns HTTP 500 status when called directly."""
        with recap_app.test_request_context('/'):
            from recap.errors import internal_error
            _, status = internal_error(Exception('simulated error'))
        assert status == 500

    def test_not_found_handler_returns_404(self, recap_app):
        """not_found_error handler returns HTTP 404 status when called directly."""
        with recap_app.test_request_context('/'):
            from recap.errors import not_found_error
            _, status = not_found_error(Exception('not found'))
        assert status == 404

    def test_internal_error_handler_rolls_back_db(self, recap_app, mocker):
        """internal_error rolls back the DB session to prevent a broken transaction."""
        mock_rollback = mocker.patch('recap.errors.db.session.rollback')
        with recap_app.test_request_context('/'):
            from recap.errors import internal_error
            internal_error(Exception('db failure'))
        mock_rollback.assert_called_once()
