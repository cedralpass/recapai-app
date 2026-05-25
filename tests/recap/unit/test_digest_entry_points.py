from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from recap.config import Config
from recap.models import Article, DigestRun, User


@pytest.mark.unit
@pytest.mark.recap
class TestDigestModelFields:
    def test_opened_at_defaults_to_none(self, recap_app, seeded_user):
        with recap_app.app_context():
            now = datetime.now(timezone.utc)
            run = DigestRun(
                user_id=seeded_user.id,
                status="completed",
                week_start=now - timedelta(days=7),
                week_end=now,
                completed_at=now,
            )
            from recap import db

            db.session.add(run)
            db.session.commit()

            fetched = db.session.get(DigestRun, run.id)
            assert fetched.opened_at is None

    def test_cluster_count_stored(self, recap_app, seeded_user):
        with recap_app.app_context():
            now = datetime.now(timezone.utc)
            run = DigestRun(
                user_id=seeded_user.id,
                status="completed",
                week_start=now - timedelta(days=7),
                week_end=now,
                completed_at=now,
                cluster_count=5,
            )
            from recap import db

            db.session.add(run)
            db.session.commit()

            fetched = db.session.get(DigestRun, run.id)
            assert fetched.cluster_count == 5


@pytest.mark.unit
@pytest.mark.recap
class TestDigestConfig:
    def test_digest_regenerate_threshold_default(self):
        assert Config.DIGEST_REGENERATE_THRESHOLD == 3


@pytest.mark.unit
@pytest.mark.recap
class TestDigestContextProcessor:
    def _make_run(self, recap_app, user_id, opened_at=None):
        from recap import db

        now = datetime.now(timezone.utc)
        run = DigestRun(
            user_id=user_id,
            status="completed",
            week_start=now - timedelta(days=7),
            week_end=now,
            completed_at=now,
            opened_at=opened_at,
            cluster_count=3,
            digest_html="<p>digest</p>",
        )
        db.session.add(run)
        db.session.commit()
        return run

    def test_has_unread_digest_true_when_opened_at_none(self, recap_app, seeded_user, unread_digest_client):
        # Visiting any authenticated page triggers the context processor.
        response = unread_digest_client.get("/")
        assert response.status_code == 200
        # The unread dot CSS class should appear in the nav
        assert b"bg-amber-400" in response.data

    def test_has_unread_digest_false_when_opened_at_set(self, recap_app, seeded_user, opened_digest_run):
        client = recap_app.test_client()
        client.post("/auth/login", data={"username": "seeduser", "password": "seedpass123"})
        response = client.get("/")
        assert response.status_code == 200
        assert b"bg-amber-400" not in response.data

    def test_has_unread_digest_false_when_no_digest(self, recap_app, seeded_authenticated_client):
        response = seeded_authenticated_client.get("/")
        assert response.status_code == 200
        assert b"bg-amber-400" not in response.data


@pytest.mark.unit
@pytest.mark.recap
class TestBookmarksSinceDigest:
    def test_bookmarks_since_digest_count(self, recap_app, seeded_user):
        """Articles created after completed_at are counted correctly."""
        from recap import db

        with recap_app.app_context():
            old_completed_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
            run = DigestRun(
                user_id=seeded_user.id,
                status="completed",
                week_start=old_completed_at - timedelta(days=7),
                week_end=old_completed_at,
                completed_at=old_completed_at,
            )
            db.session.add(run)
            db.session.commit()

            # All seed articles (created 2024-2025) are after 2020-01-01
            count = db.session.scalar(
                sa.select(sa.func.count(Article.id)).where(
                    Article.user_id == seeded_user.id,
                    Article.created > old_completed_at,
                )
            )
            assert count > 0

    def test_show_regenerate_banner_below_threshold(self, recap_app, seeded_user):
        from recap import db

        with recap_app.app_context():
            # completed_at = now means no articles are after it
            now = datetime.now(timezone.utc)
            run = DigestRun(
                user_id=seeded_user.id,
                status="completed",
                week_start=now - timedelta(days=7),
                week_end=now,
                completed_at=now,
            )
            db.session.add(run)
            db.session.commit()

            count = (
                db.session.scalar(
                    sa.select(sa.func.count(Article.id)).where(
                        Article.user_id == seeded_user.id,
                        Article.created > run.completed_at,
                    )
                )
                or 0
            )
            assert count < Config.DIGEST_REGENERATE_THRESHOLD

    def test_show_regenerate_banner_at_threshold(self, recap_app, seeded_user):
        from recap import db

        with recap_app.app_context():
            old_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
            run = DigestRun(
                user_id=seeded_user.id,
                status="completed",
                week_start=old_at - timedelta(days=7),
                week_end=old_at,
                completed_at=old_at,
            )
            db.session.add(run)
            db.session.commit()

            count = db.session.scalar(
                sa.select(sa.func.count(Article.id)).where(
                    Article.user_id == seeded_user.id,
                    Article.created > old_at,
                )
            )
            assert count >= Config.DIGEST_REGENERATE_THRESHOLD

    def test_show_regenerate_banner_above_threshold(self, recap_app, seeded_user):
        from recap import db

        with recap_app.app_context():
            old_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
            run = DigestRun(
                user_id=seeded_user.id,
                status="completed",
                week_start=old_at - timedelta(days=7),
                week_end=old_at,
                completed_at=old_at,
            )
            db.session.add(run)
            db.session.commit()

            count = db.session.scalar(
                sa.select(sa.func.count(Article.id)).where(
                    Article.user_id == seeded_user.id,
                    Article.created > old_at,
                )
            )
            assert count > Config.DIGEST_REGENERATE_THRESHOLD
