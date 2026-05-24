"""Unit tests for schedule_weekly_digests_task coordinator."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest


def _make_user(id_, digest_enabled=True):
    user = MagicMock()
    user.id = id_
    user.digest_enabled = digest_enabled
    return user


@pytest.mark.unit
@pytest.mark.recap
class TestScheduleWeeklyDigestsTask:
    """Tests for schedule_weekly_digests_task — coordinator that fans out per-user digests."""

    @patch("recap.tasks.db")
    def test_enqueues_digest_for_each_eligible_user(self, mock_db, recap_app):
        """Each user with digest_enabled=True gets a weekly_digest_task enqueued."""
        from recap import tasks

        users = [_make_user(1), _make_user(2)]
        mock_db.session.scalars.return_value.all.return_value = users

        mock_queue = MagicMock()
        with patch.object(tasks.app, "task_queue", mock_queue):
            with recap_app.app_context():
                tasks.schedule_weekly_digests_task()

        enqueue_calls = mock_queue.enqueue.call_args_list
        assert len(enqueue_calls) == 2
        for c, user in zip(enqueue_calls, users):
            assert c == call(
                "recap.tasks.weekly_digest_task",
                user.id,
                True,
                job_timeout=600,
            )

    @patch("recap.tasks.db")
    def test_send_email_flag_is_true_for_scheduled_runs(self, mock_db, recap_app):
        """Coordinator always passes send_email_flag=True to weekly_digest_task."""
        from recap import tasks

        mock_db.session.scalars.return_value.all.return_value = [_make_user(5)]

        mock_queue = MagicMock()
        with patch.object(tasks.app, "task_queue", mock_queue):
            with recap_app.app_context():
                tasks.schedule_weekly_digests_task()

        _func, user_id, send_flag = mock_queue.enqueue.call_args[0]
        assert send_flag is True

    @patch("recap.tasks.db")
    def test_empty_user_list_enqueues_nothing(self, mock_db, recap_app):
        """Zero eligible users — coordinator completes without enqueuing anything."""
        from recap import tasks

        mock_db.session.scalars.return_value.all.return_value = []

        mock_queue = MagicMock()
        with patch.object(tasks.app, "task_queue", mock_queue):
            with recap_app.app_context():
                tasks.schedule_weekly_digests_task()

        mock_queue.enqueue.assert_not_called()

    @patch("recap.tasks.db")
    def test_coordinator_does_not_self_reschedule(self, mock_db, recap_app):
        """Coordinator must NOT call enqueue_at — rescheduling is handled by the
        bash daily-digest-scheduler loop in initialize_render_run.sh."""
        from recap import tasks

        mock_db.session.scalars.return_value.all.return_value = [_make_user(3)]

        mock_queue = MagicMock()
        with patch.object(tasks.app, "task_queue", mock_queue):
            with recap_app.app_context():
                tasks.schedule_weekly_digests_task()

        mock_queue.enqueue_at.assert_not_called()
