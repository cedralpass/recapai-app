from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import click
from flask import current_app
from flask.cli import AppGroup
from rq.registry import ScheduledJobRegistry

digest_cli = AppGroup("digest", help="Digest scheduling commands.")

_PACIFIC = ZoneInfo("America/Los_Angeles")

# One-time test runs for initial rollout (May 23, 2026 Pacific).
# schedule-check registers these if they haven't passed yet; after that it falls
# through to the regular daily-at-4pm-Pacific cadence.
_TEST_8PM = datetime(2026, 5, 23, 20, 0, 0, tzinfo=_PACIFIC)
_TEST_9PM = datetime(2026, 5, 23, 21, 0, 0, tzinfo=_PACIFIC)


@digest_cli.command("schedule-check")
def schedule_check():
    """Register the digest coordinator job if not already scheduled."""

    queue = current_app.task_queue
    registry = ScheduledJobRegistry(queue=queue)

    for job_id in registry.get_job_ids():
        try:
            job = queue.fetch_job(job_id)
            if job and job.func_name == "recap.tasks.schedule_weekly_digests_task":
                click.echo(f"schedule-check: coordinator already scheduled (job_id={job_id}), skipping.")
                return
        except Exception:
            continue

    now_pacific = datetime.now(timezone.utc).astimezone(_PACIFIC)
    scheduled = []

    for label, test_time in [("8pm", _TEST_8PM), ("9pm", _TEST_9PM)]:
        if now_pacific < test_time:
            queue.enqueue_at(
                test_time.astimezone(timezone.utc),
                "recap.tasks.schedule_weekly_digests_task",
                job_timeout=60,
            )
            scheduled.append(label)

    if scheduled:
        click.echo(f"schedule-check: test runs scheduled for {' and '.join(scheduled)} PT tonight.")
    else:
        next_run = (now_pacific + timedelta(days=1)).replace(hour=16, minute=0, second=0, microsecond=0)
        queue.enqueue_at(
            next_run.astimezone(timezone.utc),
            "recap.tasks.schedule_weekly_digests_task",
            job_timeout=60,
        )
        click.echo(f"schedule-check: coordinator scheduled for {next_run.isoformat()} PT.")
