from datetime import datetime, timedelta, timezone

import click
from flask import current_app
from flask.cli import AppGroup
from rq.registry import ScheduledJobRegistry

digest_cli = AppGroup("digest", help="Digest scheduling commands.")


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

    now = datetime.now(timezone.utc)
    next_run = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    queue.enqueue_at(
        next_run,
        "recap.tasks.schedule_weekly_digests_task",
        job_timeout=60,
    )
    click.echo(f"schedule-check: coordinator scheduled for {next_run.isoformat()} UTC.")
