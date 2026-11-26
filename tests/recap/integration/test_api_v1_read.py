"""Integration tests for the read-only / iOS-app endpoints in recap/api_v1.py.

search_articles() uses pgvector SQL that SQLite can't run, so search tests mock
User.search_articles and AiApiHelper.EmbedText.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa

from recap import db
from recap.models import URL_ONLY_BLOCKED_PREFIX, Article, DigestRun, User
from tests.seed_data import SEED_CATEGORY_COUNTS

FAKE_VEC = [1.0] + [0.0] * 1535

READ_ENDPOINTS = [
    ("GET", "/api/v1/articles"),
    ("GET", "/api/v1/articles/search?q=agents"),
    ("GET", "/api/v1/articles/1"),
    ("POST", "/api/v1/articles/1/read"),
    ("DELETE", "/api/v1/articles/1"),
    ("GET", "/api/v1/categories"),
    ("GET", "/api/v1/digest/latest"),
    ("POST", "/api/v1/digest/generate"),
    ("GET", "/api/v1/digest/job/some-job"),
]


@pytest.fixture
def token(recap_app, seeded_user):
    with recap_app.app_context():
        user = db.session.get(User, seeded_user.id)
        return user.get_or_create_api_token()


@pytest.fixture
def headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_article_id(recap_app):
    """An article owned by a different user."""
    with recap_app.app_context():
        other = User(username="other", email="other@example.com")
        db.session.add(other)
        db.session.flush()
        article = Article(user_id=other.id, url_path="https://example.com/other", title="Not yours")
        db.session.add(article)
        db.session.commit()
        return article.id


def _first_article_id(recap_app, seeded_user):
    with recap_app.app_context():
        return db.session.scalar(sa.select(Article.id).where(Article.user_id == seeded_user.id).limit(1))


@pytest.mark.integration
@pytest.mark.recap
class TestReadApiAuth:
    @pytest.mark.parametrize("method,path", READ_ENDPOINTS)
    def test_401_without_token(self, recap_client, method, path):
        response = recap_client.open(path, method=method)
        assert response.status_code == 401
        assert response.get_json()["error"]

    @pytest.mark.parametrize("method,path", READ_ENDPOINTS)
    def test_401_with_bad_token(self, recap_client, seeded_user, method, path):
        response = recap_client.open(path, method=method, headers={"Authorization": "Bearer nope"})
        assert response.status_code == 401

    @pytest.mark.parametrize(
        "method,suffix",
        [("GET", ""), ("POST", "/read"), ("DELETE", "")],
    )
    def test_other_users_article_is_404(self, recap_app, recap_client, headers, other_article_id, method, suffix):
        response = recap_client.open(f"/api/v1/articles/{other_article_id}{suffix}", method=method, headers=headers)
        assert response.status_code == 404
        with recap_app.app_context():
            article = db.session.get(Article, other_article_id)
            assert article is not None
            assert article.is_read is False


@pytest.mark.integration
@pytest.mark.recap
class TestListArticles:
    def test_first_page_newest_first(self, recap_client, headers):
        response = recap_client.get("/api/v1/articles?per_page=10", headers=headers)
        assert response.status_code == 200
        body = response.get_json()
        assert body["page"] == 1
        assert body["has_next"] is True
        assert len(body["articles"]) == 10
        created = [a["created"] for a in body["articles"]]
        assert created == sorted(created, reverse=True)

    def test_article_shape(self, recap_client, headers):
        article = recap_client.get("/api/v1/articles", headers=headers).get_json()["articles"][0]
        assert set(article) == {
            "id",
            "url",
            "title",
            "summary",
            "author",
            "category",
            "key_topics",
            "source",
            "created",
            "read",
            "summary_available",
        }
        assert isinstance(article["key_topics"], list) and article["key_topics"]
        assert article["created"].endswith("Z")
        assert article["read"] is False
        assert article["summary_available"] is True
        assert "content_text" not in article

    def test_pages_cover_all_articles_without_overlap(self, recap_client, headers):
        seen = []
        page = 1
        while True:
            body = recap_client.get(f"/api/v1/articles?page={page}&per_page=20", headers=headers).get_json()
            seen.extend(a["id"] for a in body["articles"])
            if not body["has_next"]:
                break
            page += 1
        assert page == 3
        assert len(seen) == len(set(seen)) == sum(SEED_CATEGORY_COUNTS.values())

    def test_page_past_end_is_empty(self, recap_client, headers):
        body = recap_client.get("/api/v1/articles?page=99", headers=headers).get_json()
        assert body["articles"] == []
        assert body["has_next"] is False

    def test_per_page_is_capped(self, recap_client, headers):
        body = recap_client.get("/api/v1/articles?per_page=500", headers=headers).get_json()
        assert len(body["articles"]) == 50

    def test_category_filter(self, recap_client, headers):
        body = recap_client.get(
            "/api/v1/articles?category=Artificial Intelligence&per_page=50", headers=headers
        ).get_json()
        assert len(body["articles"]) == 27
        assert {a["category"] for a in body["articles"]} == {"Artificial Intelligence"}

    def test_read_articles_are_not_moved_to_the_end(self, recap_app, recap_client, headers, seeded_user):
        """Unlike the web list, the API is purely newest first."""
        newest_id = recap_client.get("/api/v1/articles", headers=headers).get_json()["articles"][0]["id"]
        # seeded_user's app context is still pushed and requests reuse it, so write through that session.
        db.session.get(Article, newest_id).is_read = True
        db.session.commit()
        first = recap_client.get("/api/v1/articles", headers=headers).get_json()["articles"][0]
        assert first["id"] == newest_id
        assert first["read"] is True

    def test_url_only_article_has_no_summary_available(self, recap_app, recap_client, headers, seeded_user):
        with recap_app.app_context():
            article = Article(
                user_id=seeded_user.id,
                url_path="https://blocked.example.com/post",
                summary=URL_ONLY_BLOCKED_PREFIX + "Probably about something.",
                created=datetime(2030, 1, 1),
            )
            db.session.add(article)
            db.session.commit()
        first = recap_client.get("/api/v1/articles", headers=headers).get_json()["articles"][0]
        assert first["url"] == "https://blocked.example.com/post"
        assert first["summary_available"] is False
        assert first["key_topics"] == []


@pytest.mark.integration
@pytest.mark.recap
class TestArticleDetailReadDelete:
    def test_get_article(self, recap_app, recap_client, headers, seeded_user):
        article_id = _first_article_id(recap_app, seeded_user)
        response = recap_client.get(f"/api/v1/articles/{article_id}", headers=headers)
        assert response.status_code == 200
        assert response.get_json()["id"] == article_id

    def test_missing_article_404(self, recap_client, headers):
        assert recap_client.get("/api/v1/articles/999999", headers=headers).status_code == 404

    def test_set_read_true_then_false(self, recap_app, recap_client, headers, seeded_user):
        article_id = _first_article_id(recap_app, seeded_user)
        response = recap_client.post(f"/api/v1/articles/{article_id}/read", json={"read": True}, headers=headers)
        assert response.status_code == 200
        assert response.get_json()["read"] is True
        # idempotent
        response = recap_client.post(f"/api/v1/articles/{article_id}/read", json={"read": True}, headers=headers)
        assert response.get_json()["read"] is True
        response = recap_client.post(f"/api/v1/articles/{article_id}/read", json={"read": False}, headers=headers)
        assert response.get_json()["read"] is False
        with recap_app.app_context():
            assert db.session.get(Article, article_id).is_read is False

    def test_read_without_body_toggles(self, recap_app, recap_client, headers, seeded_user):
        article_id = _first_article_id(recap_app, seeded_user)
        assert recap_client.post(f"/api/v1/articles/{article_id}/read", headers=headers).get_json()["read"] is True
        assert recap_client.post(f"/api/v1/articles/{article_id}/read", headers=headers).get_json()["read"] is False

    def test_read_rejects_non_bool(self, recap_app, recap_client, headers, seeded_user):
        article_id = _first_article_id(recap_app, seeded_user)
        response = recap_client.post(f"/api/v1/articles/{article_id}/read", json={"read": "yes"}, headers=headers)
        assert response.status_code == 400

    def test_delete(self, recap_app, recap_client, headers, seeded_user):
        article_id = _first_article_id(recap_app, seeded_user)
        response = recap_client.delete(f"/api/v1/articles/{article_id}", headers=headers)
        assert response.status_code == 200
        assert response.get_json() == {"status": "deleted", "id": article_id}
        with recap_app.app_context():
            assert db.session.get(Article, article_id) is None
        assert recap_client.delete(f"/api/v1/articles/{article_id}", headers=headers).status_code == 404


@pytest.mark.integration
@pytest.mark.recap
class TestCategories:
    def test_categories_with_counts(self, recap_client, headers):
        body = recap_client.get("/api/v1/categories", headers=headers).get_json()
        assert {c["name"]: c["count"] for c in body["categories"]} == SEED_CATEGORY_COUNTS
        assert body["categories"][0] == {"name": "Artificial Intelligence", "count": 27}

    def test_unclassified_articles_left_out(self, recap_app, recap_client, headers, seeded_user):
        with recap_app.app_context():
            db.session.add(Article(user_id=seeded_user.id, url_path="https://example.com/pending"))
            db.session.commit()
        names = [c["name"] for c in recap_client.get("/api/v1/categories", headers=headers).get_json()["categories"]]
        assert None not in names


@pytest.mark.integration
@pytest.mark.recap
class TestSearch:
    def test_returns_matches(self, recap_app, recap_client, headers, seeded_articles):
        ai = [a for a in seeded_articles if a.category == "Artificial Intelligence"][:3]
        with (
            patch("recap.queries.AiApiHelper.EmbedText", return_value=FAKE_VEC) as embed,
            patch.object(User, "search_articles", return_value=ai) as search,
        ):
            response = recap_client.get(
                "/api/v1/articles/search?q=agents&category=Artificial Intelligence", headers=headers
            )
        assert response.status_code == 200
        body = response.get_json()
        assert body["query"] == "agents"
        assert [a["id"] for a in body["articles"]] == [a.id for a in ai]
        embed.assert_called_once_with("agents")
        search.assert_called_once_with(FAKE_VEC, limit=20, category="Artificial Intelligence")

    def test_blank_query_skips_embedding(self, recap_client, headers):
        with patch("recap.queries.AiApiHelper.EmbedText") as embed:
            body = recap_client.get("/api/v1/articles/search?q=  ", headers=headers).get_json()
        assert body["articles"] == []
        embed.assert_not_called()

    def test_failed_embedding_returns_empty(self, recap_client, headers):
        with (
            patch("recap.queries.AiApiHelper.EmbedText", return_value=None),
            patch.object(User, "search_articles") as search,
        ):
            body = recap_client.get("/api/v1/articles/search?q=agents", headers=headers).get_json()
        assert body["articles"] == []
        search.assert_not_called()


@pytest.mark.integration
@pytest.mark.recap
class TestDigest:
    def test_no_digest_returns_none(self, recap_client, headers):
        response = recap_client.get("/api/v1/digest/latest", headers=headers)
        assert response.status_code == 404
        assert response.get_json() == {"status": "none", "articles_since_last": 52}

    def test_latest_digest_payload_and_marks_opened(self, recap_app, recap_client, headers, completed_digest_run):
        response = recap_client.get("/api/v1/digest/latest", headers=headers)
        assert response.status_code == 200
        body = response.get_json()
        assert body["id"] == completed_digest_run.id
        assert body["article_count"] == 12
        assert body["cluster_count"] == 3
        assert body["digest_html"] == "<p>Test digest</p>"
        assert body["bookmarks_since"] == 0
        assert body["show_regenerate"] is False
        assert body["was_unread"] is True
        assert body["week_start"] == completed_digest_run.week_start.date().isoformat()
        with recap_app.app_context():
            assert db.session.get(DigestRun, completed_digest_run.id).opened_at is not None
        # second fetch: already opened
        assert recap_client.get("/api/v1/digest/latest", headers=headers).get_json()["was_unread"] is False

    def test_peek_does_not_mark_opened(self, recap_app, recap_client, headers, completed_digest_run):
        body = recap_client.get("/api/v1/digest/latest?mark_opened=false", headers=headers).get_json()
        assert body["was_unread"] is True
        with recap_app.app_context():
            assert db.session.get(DigestRun, completed_digest_run.id).opened_at is None
        assert recap_client.get("/api/v1/digest/latest", headers=headers).get_json()["was_unread"] is True

    def test_stale_digest_offers_regenerate(self, recap_app, recap_client, headers, seeded_user):
        with recap_app.app_context():
            old = datetime(2020, 1, 1, tzinfo=timezone.utc)
            db.session.add(
                DigestRun(
                    user_id=seeded_user.id,
                    status="completed",
                    week_start=old - timedelta(days=7),
                    week_end=old,
                    completed_at=old,
                    digest_html="<p>Old</p>",
                )
            )
            db.session.commit()
        body = recap_client.get("/api/v1/digest/latest", headers=headers).get_json()
        assert body["bookmarks_since"] == 52
        assert body["show_regenerate"] is True

    def test_running_digest_is_not_latest(self, recap_app, recap_client, headers, seeded_user):
        with recap_app.app_context():
            now = datetime.now(timezone.utc)
            db.session.add(
                DigestRun(user_id=seeded_user.id, status="running", week_start=now - timedelta(days=7), week_end=now)
            )
            db.session.commit()
        assert recap_client.get("/api/v1/digest/latest", headers=headers).status_code == 404

    def test_generate_enqueues_job(self, recap_app, recap_client, headers, seeded_user, mocker):
        job = MagicMock()
        job.id = "digest-job-1"
        enqueue = mocker.patch.object(recap_app.task_queue, "enqueue", return_value=job)
        response = recap_client.post("/api/v1/digest/generate", headers=headers)
        assert response.status_code == 202
        assert response.get_json() == {"status": "queued", "job_id": "digest-job-1"}
        enqueue.assert_called_once_with("recap.tasks.weekly_digest_task", seeded_user.id, False, job_timeout=600)

    def _mock_job(self, user_id, func_name="recap.tasks.weekly_digest_task", status="finished"):
        from rq.job import JobStatus

        job = MagicMock()
        job.func_name = func_name
        job.args = (user_id, False)
        job.get_status.return_value = JobStatus(status)
        return job

    def test_job_status(self, recap_app, recap_client, headers, seeded_user, mocker):
        mocker.patch.object(recap_app.task_queue, "fetch_job", return_value=self._mock_job(seeded_user.id))
        response = recap_client.get("/api/v1/digest/job/abc", headers=headers)
        assert response.status_code == 200
        assert response.get_json() == {"status": "finished"}

    def test_unknown_job_404(self, recap_app, recap_client, headers, mocker):
        mocker.patch.object(recap_app.task_queue, "fetch_job", return_value=None)
        response = recap_client.get("/api/v1/digest/job/abc", headers=headers)
        assert response.status_code == 404
        assert response.get_json() == {"status": "not_found"}

    def test_other_users_job_404(self, recap_app, recap_client, headers, seeded_user, mocker):
        mocker.patch.object(recap_app.task_queue, "fetch_job", return_value=self._mock_job(seeded_user.id + 1))
        assert recap_client.get("/api/v1/digest/job/abc", headers=headers).status_code == 404

    def test_non_digest_job_404(self, recap_app, recap_client, headers, seeded_user, mocker):
        job = self._mock_job(seeded_user.id, func_name="recap.tasks.classify_url")
        mocker.patch.object(recap_app.task_queue, "fetch_job", return_value=job)
        assert recap_client.get("/api/v1/digest/job/abc", headers=headers).status_code == 404
