"""Unit tests for the 'flask digest' CLI commands."""

from unittest.mock import MagicMock, patch

import pytest

# recap.tasks pushes a global app context at import time.
# Flask's with_appcontext skips pushing a new one when a context is already
# active, so current_app inside the CLI command resolves to tasks.app.
# Patching tasks.app.task_queue ensures the mock is seen regardless of whether
# this module runs alone or after other tests that already imported recap.tasks.


@pytest.mark.unit
@pytest.mark.recap
class TestDigestScheduleCheck:
    """Tests for 'flask digest schedule-check' CLI command."""

    def test_registers_coordinator_when_registry_empty(self, recap_runner):
        """Empty registry → enqueue_at is called and output confirms the schedule."""
        from recap import tasks

        mock_queue = MagicMock()
        registry = MagicMock()
        registry.get_job_ids.return_value = []

        with (
            patch.object(tasks.app, "task_queue", mock_queue),
            patch("recap.cli.ScheduledJobRegistry", return_value=registry),
        ):
            result = recap_runner.invoke(args=["digest", "schedule-check"])

        assert result.exit_code == 0
        assert mock_queue.enqueue_at.call_count >= 1
        assert "scheduled for" in result.output or "test runs scheduled" in result.output

    def test_skips_when_coordinator_already_present(self, recap_runner):
        """Registry already has the coordinator job → enqueue_at not called."""
        from recap import tasks

        mock_queue = MagicMock()
        existing_job = MagicMock()
        existing_job.func_name = "recap.tasks.schedule_weekly_digests_task"
        mock_queue.fetch_job.return_value = existing_job

        registry = MagicMock()
        registry.get_job_ids.return_value = ["existing-job-id"]

        with (
            patch.object(tasks.app, "task_queue", mock_queue),
            patch("recap.cli.ScheduledJobRegistry", return_value=registry),
        ):
            result = recap_runner.invoke(args=["digest", "schedule-check"])

        assert result.exit_code == 0
        mock_queue.enqueue_at.assert_not_called()
        assert "already scheduled" in result.output

    def test_registers_when_different_job_in_registry(self, recap_runner):
        """Registry has a different job (not the coordinator) → enqueue_at IS called."""
        from recap import tasks

        mock_queue = MagicMock()
        other_job = MagicMock()
        other_job.func_name = "recap.tasks.weekly_digest_task"
        mock_queue.fetch_job.return_value = other_job

        registry = MagicMock()
        registry.get_job_ids.return_value = ["other-job-id"]

        with (
            patch.object(tasks.app, "task_queue", mock_queue),
            patch("recap.cli.ScheduledJobRegistry", return_value=registry),
        ):
            result = recap_runner.invoke(args=["digest", "schedule-check"])

        assert result.exit_code == 0
        assert mock_queue.enqueue_at.call_count >= 1
        assert "scheduled for" in result.output or "test runs scheduled" in result.output

    def test_scheduled_func_name_is_coordinator(self, recap_runner):
        """The job registered by schedule-check targets the coordinator function."""
        from recap import tasks

        mock_queue = MagicMock()
        registry = MagicMock()
        registry.get_job_ids.return_value = []

        with (
            patch.object(tasks.app, "task_queue", mock_queue),
            patch("recap.cli.ScheduledJobRegistry", return_value=registry),
        ):
            recap_runner.invoke(args=["digest", "schedule-check"])

        _at_dt, func_name = mock_queue.enqueue_at.call_args[0][:2]
        assert func_name == "recap.tasks.schedule_weekly_digests_task"

    def test_fetch_job_exception_is_tolerated(self, recap_runner):
        """If fetch_job raises (e.g. stale job ID), the command recovers and still registers."""
        from recap import tasks

        mock_queue = MagicMock()
        mock_queue.fetch_job.side_effect = Exception("stale job")

        registry = MagicMock()
        registry.get_job_ids.return_value = ["stale-id"]

        with (
            patch.object(tasks.app, "task_queue", mock_queue),
            patch("recap.cli.ScheduledJobRegistry", return_value=registry),
        ):
            result = recap_runner.invoke(args=["digest", "schedule-check"])

        assert result.exit_code == 0
        assert mock_queue.enqueue_at.call_count >= 1
