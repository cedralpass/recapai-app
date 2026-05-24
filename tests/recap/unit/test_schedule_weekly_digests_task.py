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
    def test_empty_user_list_still_reschedules(self, mock_db, recap_app):
        """Zero eligible users — coordinator must still self-reschedule."""
        from recap import tasks

        mock_db.session.scalars.return_value.all.return_value = []

        mock_queue = MagicMock()
        with patch.object(tasks.app, "task_queue", mock_queue):
            with recap_app.app_context():
                tasks.schedule_weekly_digests_task()

        mock_queue.enqueue.assert_not_called()
        mock_queue.enqueue_at.assert_called_once()

    @patch("recap.tasks.db")
    def test_self_reschedules_via_enqueue_at(self, mock_db, recap_app):
        """After enqueuing per-user digests, coordinator schedules itself via enqueue_at."""
        from recap import tasks

        mock_db.session.scalars.return_value.all.return_value = [_make_user(3)]

        mock_queue = MagicMock()
        with patch.object(tasks.app, "task_queue", mock_queue):
            with recap_app.app_context():
                tasks.schedule_weekly_digests_task()

        mock_queue.enqueue_at.assert_called_once()
        at_dt, func_name = mock_queue.enqueue_at.call_args[0][:2]
        assert func_name == "recap.tasks.schedule_weekly_digests_task"
        assert isinstance(at_dt, datetime)

    @patch("recap.tasks.db")
    def test_reschedule_datetime_is_tomorrow_4pm_pacific(self, mock_db, recap_app):
        """The rescheduled datetime is tomorrow at 4pm Pacific time."""
        from datetime import timedelta
        from zoneinfo import ZoneInfo

        from recap import tasks

        mock_db.session.scalars.return_value.all.return_value = []

        mock_queue = MagicMock()
        now = datetime.now(timezone.utc)
        with patch.object(tasks.app, "task_queue", mock_queue):
            with recap_app.app_context():
                tasks.schedule_weekly_digests_task()

        at_dt = mock_queue.enqueue_at.call_args[0][0]
        pacific = ZoneInfo("America/Los_Angeles")
        at_dt_pacific = at_dt.astimezone(pacific)
        assert at_dt_pacific.hour == 16
        assert at_dt_pacific.minute == 0
        assert at_dt_pacific.second == 0
        assert at_dt > now
        assert at_dt < now + timedelta(days=2)

    @patch("recap.tasks.db")
    def test_reschedule_datetime_is_timezone_aware(self, mock_db, recap_app):
        """The enqueue_at datetime must be timezone-aware (RQ 2.x requirement)."""
        from recap import tasks

        mock_db.session.scalars.return_value.all.return_value = []

        mock_queue = MagicMock()
        with patch.object(tasks.app, "task_queue", mock_queue):
            with recap_app.app_context():
                tasks.schedule_weekly_digests_task()

        at_dt = mock_queue.enqueue_at.call_args[0][0]
        assert at_dt.tzinfo is not None
