from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from recap import db
from recap.models import Article, DigestRun


def _make_mock_job(job_id="test-job-123"):
    mock = MagicMock()
    mock.id = job_id
    return mock


@pytest.mark.integration
@pytest.mark.recap
class TestDigestPageRoute:
    def test_digest_page_requires_login(self, recap_client):
        response = recap_client.get("/digest")
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_digest_page_no_digest_redirects_home(self, seeded_authenticated_client):
        response = seeded_authenticated_client.get("/digest", follow_redirects=True)
        assert response.status_code == 200
        assert b"No digest yet" in response.data or b"generate" in response.data.lower()

    def test_digest_page_renders_digest_html(self, recap_app, unread_digest_client):
        response = unread_digest_client.get("/digest")
        assert response.status_code == 200
        assert b"Test digest" in response.data

    def test_digest_page_sets_opened_at_on_first_view(
        self, recap_app, seeded_user, completed_digest_run, unread_digest_client
    ):
        with recap_app.app_context():
            run = db.session.get(DigestRun, completed_digest_run.id)
            assert run.opened_at is None

        unread_digest_client.get("/digest")

        with recap_app.app_context():
            run = db.session.get(DigestRun, completed_digest_run.id)
            assert run.opened_at is not None

    def test_digest_page_does_not_overwrite_opened_at(
        self, recap_app, seeded_user, completed_digest_run, unread_digest_client
    ):
        unread_digest_client.get("/digest")

        with recap_app.app_context():
            run = db.session.get(DigestRun, completed_digest_run.id)
            first_opened = run.opened_at

        unread_digest_client.get("/digest")

        with recap_app.app_context():
            run = db.session.get(DigestRun, completed_digest_run.id)
            assert run.opened_at == first_opened

    def test_digest_page_no_regenerate_banner_below_threshold(self, recap_app, unread_digest_client):
        # completed_at = now means 0 articles after it — below threshold
        response = unread_digest_client.get("/digest")
        assert response.status_code == 200
        assert b"Regenerate" not in response.data

    def test_digest_page_shows_regenerate_banner_at_threshold(self, recap_app, seeded_user, mocker):
        # Create a stale digest (completed in 2020) so seed articles count as new bookmarks
        with recap_app.app_context():
            old_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
            run = DigestRun(
                user_id=seeded_user.id,
                status="completed",
                week_start=old_at - timedelta(days=7),
                week_end=old_at,
                completed_at=old_at,
                article_count=5,
                cluster_count=2,
                digest_html="<p>Old digest</p>",
                digest_text="Old digest",
                sent=True,
            )
            db.session.add(run)
            db.session.commit()

        client = recap_app.test_client()
        client.post("/auth/login", data={"username": "seeduser", "password": "seedpass123"})
        response = client.get("/digest")
        assert response.status_code == 200
        assert b"Regenerate" in response.data
        assert b"new bookmark" in response.data


@pytest.mark.integration
@pytest.mark.recap
class TestDigestGenerateRoute:
    def test_digest_generate_requires_login(self, recap_client):
        response = recap_client.post("/digest/generate")
        assert response.status_code == 302

    def test_digest_generate_enqueues_job(self, recap_app, seeded_authenticated_client, mocker):
        mock_job = _make_mock_job()
        mocker.patch.object(recap_app.task_queue, "enqueue", return_value=mock_job)

        response = seeded_authenticated_client.post("/digest/generate")
        assert response.status_code == 200
        recap_app.task_queue.enqueue.assert_called_once()

    def test_digest_generate_job_id_in_response(self, recap_app, seeded_authenticated_client, mocker):
        mock_job = _make_mock_job("my-test-job-id")
        mocker.patch.object(recap_app.task_queue, "enqueue", return_value=mock_job)

        response = seeded_authenticated_client.post("/digest/generate")
        data = response.get_json()
        assert data["job_id"] == "my-test-job-id"
        assert data["status"] == "queued"


@pytest.mark.integration
@pytest.mark.recap
class TestDigestRegenerateRoute:
    def test_digest_regenerate_requires_login(self, recap_client):
        response = recap_client.post("/digest/999/regenerate")
        assert response.status_code == 302

    def test_digest_regenerate_enqueues_job(
        self, recap_app, seeded_user, completed_digest_run, unread_digest_client, mocker
    ):
        mock_job = _make_mock_job()
        mocker.patch.object(recap_app.task_queue, "enqueue", return_value=mock_job)

        response = unread_digest_client.post(f"/digest/{completed_digest_run.id}/regenerate")
        assert response.status_code == 200
        data = response.get_json()
        assert "job_id" in data

    def test_digest_regenerate_404_on_wrong_user(self, recap_app, seeded_user, completed_digest_run, mocker):
        # Create a second user and log in as them
        with recap_app.app_context():
            from recap.models import User

            other = User(username="otheruser", email="other@example.com")
            other.set_password("otherpass123")
            db.session.add(other)
            db.session.commit()

        other_client = recap_app.test_client()
        other_client.post("/auth/login", data={"username": "otheruser", "password": "otherpass123"})

        response = other_client.post(f"/digest/{completed_digest_run.id}/regenerate")
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.recap
class TestDigestJobStatusRoute:
    def test_digest_job_status_queued(self, recap_app, seeded_authenticated_client, mocker):
        mock_job = MagicMock()
        mock_job.get_status.return_value = "queued"
        mocker.patch.object(recap_app.task_queue, "fetch_job", return_value=mock_job)

        response = seeded_authenticated_client.get("/digest/job/some-job-id")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "queued"

    def test_digest_job_status_finished_includes_view_url(self, recap_app, seeded_authenticated_client, mocker):
        mock_job = MagicMock()
        mock_job.get_status.return_value = "finished"
        mocker.patch.object(recap_app.task_queue, "fetch_job", return_value=mock_job)

        response = seeded_authenticated_client.get("/digest/job/some-job-id")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "finished"
        assert data["view_url"] == "/digest"
