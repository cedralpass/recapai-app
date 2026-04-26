"""Integration tests for recap/profile — user, edit_profile, organize_taxonomy, apply_taxonomy."""
import json
import os
import pytest
import sqlalchemy as sa
from unittest.mock import patch
from recap.models import User, Article
from recap import db


@pytest.mark.integration
@pytest.mark.recap
class TestUserProfileRoute:
    def test_user_profile_returns_200(self, authenticated_client, recap_app, test_user):
        """GET /user/<username> returns 200 for an existing user."""
        with recap_app.app_context():
            username = test_user.username

        response = authenticated_client.get(f'/user/{username}')
        assert response.status_code == 200

    def test_user_profile_shows_username(self, authenticated_client, recap_app, test_user):
        """The profile page renders the user's username."""
        with recap_app.app_context():
            username = test_user.username

        response = authenticated_client.get(f'/user/{username}')
        assert username.encode() in response.data

    def test_user_profile_with_articles(self, authenticated_client, recap_app, test_user):
        """Articles owned by the user are visible on their profile page."""
        with recap_app.app_context():
            db.session.add(Article(
                url_path='https://example.com/profile-article',
                user_id=test_user.id,
            ))
            db.session.commit()
            username = test_user.username

        response = authenticated_client.get(f'/user/{username}')
        assert response.status_code == 200
        assert b'profile-article' in response.data

    def test_user_profile_404_for_unknown_user(self, authenticated_client):
        """GET /user/<nonexistent> returns 404."""
        response = authenticated_client.get('/user/nobody-exists-xyz')
        assert response.status_code == 404

    def test_user_profile_requires_login(self, recap_client, recap_app, test_user):
        """Unauthenticated GET redirects to login."""
        with recap_app.app_context():
            username = test_user.username

        response = recap_client.get(f'/user/{username}')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.integration
@pytest.mark.recap
class TestEditProfileRoute:
    def test_get_prepopulates_form_with_current_values(
        self, authenticated_client, recap_app, test_user
    ):
        """GET /edit_profile renders form pre-filled with the current user's data."""
        with recap_app.app_context():
            username = test_user.username
            email = test_user.email

        response = authenticated_client.get('/edit_profile')
        assert response.status_code == 200
        assert username.encode() in response.data
        assert email.encode() in response.data

    def test_post_updates_username(self, authenticated_client, recap_app, test_user):
        """POST /edit_profile with a new username persists the change."""
        with recap_app.app_context():
            user_id = test_user.id

        response = authenticated_client.post(
            '/edit_profile',
            data={
                'username': 'updateduser',
                'email': 'test@example.com',
                'phone': '1234567890',
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'Your changes have been saved' in response.data

        with recap_app.app_context():
            user = db.session.get(User, user_id)
            assert user.username == 'updateduser'

    def test_post_duplicate_username_shows_error(
        self, authenticated_client, recap_app, test_user
    ):
        """POST with an already-taken username shows a validation error."""
        with recap_app.app_context():
            other = User(username='takenuser', email='taken@example.com')
            other.set_password('pass')
            db.session.add(other)
            db.session.commit()

        response = authenticated_client.post(
            '/edit_profile',
            data={
                'username': 'takenuser',
                'email': 'test@example.com',
                'phone': '1234567890',
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'different username' in response.data

    def test_edit_profile_requires_login(self, recap_client):
        """Unauthenticated GET redirects to login."""
        response = recap_client.get('/edit_profile')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.integration
@pytest.mark.recap
class TestOrganizeTaxonomyRoute:
    @patch('recap.profile.AiApiHelper')
    def test_organize_taxonomy_returns_200(
        self, mock_ai, authenticated_client, recap_app, test_user
    ):
        """GET /organize_taxonomy returns 200 when AI responds successfully."""
        mock_ai.PerformTask.return_value = {
            'description': 'Consolidated some overlapping categories.',
            'mappings': [
                {'old_category': 'Tech', 'new_category': 'Technology'},
            ],
        }

        with recap_app.app_context():
            db.session.add(Article(
                url_path='https://a.com/1', user_id=test_user.id, category='Tech',
            ))
            db.session.commit()

        response = authenticated_client.get('/organize_taxonomy')
        assert response.status_code == 200

    @patch('recap.profile.AiApiHelper')
    def test_organize_taxonomy_shows_ai_description(
        self, mock_ai, authenticated_client, recap_app, test_user
    ):
        """The AI-generated description appears in the rendered page."""
        mock_ai.PerformTask.return_value = {
            'description': 'Merged Tech and Software into Technology.',
            'mappings': [
                {'old_category': 'Tech', 'new_category': 'Technology'},
                {'old_category': 'Software', 'new_category': 'Technology'},
            ],
        }

        with recap_app.app_context():
            db.session.add(Article(
                url_path='https://a.com/2', user_id=test_user.id, category='Tech',
            ))
            db.session.commit()

        response = authenticated_client.get('/organize_taxonomy')
        assert b'Merged Tech and Software into Technology.' in response.data

    @patch('recap.profile.AiApiHelper')
    def test_organize_taxonomy_stores_mapping_in_session(
        self, mock_ai, authenticated_client, recap_app, test_user
    ):
        """After the AI call, the category mapping is stored in the session."""
        mock_ai.PerformTask.return_value = {
            'description': 'Some changes.',
            'mappings': [{'old_category': 'Tech', 'new_category': 'Technology'}],
        }

        with recap_app.app_context():
            db.session.add(Article(
                url_path='https://a.com/3', user_id=test_user.id, category='Tech',
            ))
            db.session.commit()

        authenticated_client.get('/organize_taxonomy')

        with authenticated_client.session_transaction() as sess:
            assert 'category_mapping' in sess
            assert sess['category_mapping'] == {'Tech': 'Technology'}

    def test_organize_taxonomy_requires_login(self, recap_client):
        """Unauthenticated GET redirects to login."""
        response = recap_client.get('/organize_taxonomy')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.integration
@pytest.mark.recap
class TestApplyTaxonomyRoute:
    def test_apply_taxonomy_updates_article_categories(
        self, authenticated_client, recap_app, test_user
    ):
        """POST /apply_taxonomy remaps article categories per the session mapping."""
        with recap_app.app_context():
            article = Article(
                url_path='https://a.com/remap', user_id=test_user.id, category='Tech',
            )
            db.session.add(article)
            db.session.commit()
            article_id = article.id

        with authenticated_client.session_transaction() as sess:
            sess['category_mapping'] = {'Tech': 'Technology'}

        response = authenticated_client.post('/apply_taxonomy', follow_redirects=True)
        assert response.status_code == 200
        assert b'updated successfully' in response.data

        with recap_app.app_context():
            updated = db.session.get(Article, article_id)
            assert updated.category == 'Technology'

    def test_apply_taxonomy_clears_session_mapping(
        self, authenticated_client, recap_app, test_user
    ):
        """After applying, category_mapping is removed from the session."""
        with recap_app.app_context():
            db.session.add(Article(
                url_path='https://a.com/clear', user_id=test_user.id, category='Tech',
            ))
            db.session.commit()

        with authenticated_client.session_transaction() as sess:
            sess['category_mapping'] = {'Tech': 'Technology'}

        authenticated_client.post('/apply_taxonomy', follow_redirects=True)

        with authenticated_client.session_transaction() as sess:
            assert 'category_mapping' not in sess

    def test_apply_taxonomy_without_session_redirects(
        self, authenticated_client
    ):
        """POST without a session mapping redirects to organize_taxonomy."""
        response = authenticated_client.post('/apply_taxonomy', follow_redirects=False)
        assert response.status_code == 302
        assert 'organize_taxonomy' in response.headers['Location']

    def test_apply_taxonomy_requires_login(self, recap_client):
        """Unauthenticated POST redirects to login."""
        response = recap_client.post('/apply_taxonomy')
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


@pytest.mark.unit
@pytest.mark.recap
class TestCreateCategoryMapping:
    def test_converts_list_to_dict(self, recap_app):
        """create_category_mapping converts the AI mappings list to a dict."""
        from recap.profile import create_category_mapping

        mappings = [
            {'old_category': 'Tech', 'new_category': 'Technology'},
            {'old_category': 'AI', 'new_category': 'Artificial Intelligence'},
        ]
        result = create_category_mapping(mappings)
        assert result == {
            'Tech': 'Technology',
            'AI': 'Artificial Intelligence',
        }

    def test_returns_empty_dict_for_empty_list(self, recap_app):
        """create_category_mapping returns {} for an empty mappings list."""
        from recap.profile import create_category_mapping
        assert create_category_mapping([]) == {}


# ---------------------------------------------------------------------------
# Helpers shared by the seed-data taxonomy tests
# ---------------------------------------------------------------------------

def _load_seed_fixture():
    """Load the recorded AI response fixture for seed-data taxonomy tests."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),        # tests/recap/integration/
        '..', '..', 'fixtures',
        'organize_taxonomy_seed_response.json',
    )
    with open(os.path.abspath(fixture_path)) as f:
        return json.load(f)


def _build_mapping_from_fixture(fixture):
    """Return a {old: new} dict from the fixture's mappings list."""
    from recap.profile import create_category_mapping
    return create_category_mapping(fixture['mappings'])


def _article_counts_by_category(recap_app, user_id):
    """Return {category: count} for all articles owned by user_id."""
    with recap_app.app_context():
        rows = db.session.execute(
            sa.select(Article.category, sa.func.count(Article.id))
            .where(Article.user_id == user_id)
            .group_by(Article.category)
        ).all()
    return {row[0]: row[1] for row in rows}


# ---------------------------------------------------------------------------
# organize_taxonomy — with realistic seed data
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.recap
class TestOrganizeTaxonomyWithSeedData:
    """Verify organize_taxonomy stores a complete, well-formed mapping for a real dataset."""

    @patch('recap.profile.AiApiHelper')
    def test_session_mapping_covers_fixture_categories(
        self, mock_ai, seeded_authenticated_client, seeded_user, recap_app
    ):
        """
        Every old_category in the recorded fixture must appear as a key in the
        session mapping after organize_taxonomy runs.

        Note: the recorded fixture may not cover every seed category — the AI
        occasionally omits low-frequency categories (e.g. Neuroscience was absent
        from the fixture recorded on 2026-04-26). That is a known AI limitation
        documented by test_session_mapping_old_categories_match_db_exactly, which
        verifies that whatever IS in the mapping matches the DB exactly.
        """
        fixture = _load_seed_fixture()
        fixture_old_categories = {m['old_category'] for m in fixture['mappings']}
        mock_ai.PerformTask.return_value = fixture

        seeded_authenticated_client.get('/organize_taxonomy')

        with seeded_authenticated_client.session_transaction() as sess:
            mapping = sess.get('category_mapping', {})

        missing = fixture_old_categories - set(mapping.keys())
        assert missing == set(), (
            f"organize_taxonomy session mapping is missing fixture categories: {missing}"
        )

    @patch('recap.profile.AiApiHelper')
    def test_session_mapping_old_categories_match_db_exactly(
        self, mock_ai, seeded_authenticated_client, seeded_user, recap_app
    ):
        """
        Every old_category key in the mapping must exactly match a category string
        stored in the database.  A mismatch means apply_taxonomy will silently skip
        those articles.
        """
        fixture = _load_seed_fixture()
        mock_ai.PerformTask.return_value = fixture

        with recap_app.app_context():
            db_categories = {
                row[0] for row in db.session.execute(
                    sa.select(Article.category).where(Article.user_id == seeded_user.id).distinct()
                ).all()
                if row[0] is not None
            }

        seeded_authenticated_client.get('/organize_taxonomy')

        with seeded_authenticated_client.session_transaction() as sess:
            mapping = sess.get('category_mapping', {})

        unmatched = set(mapping.keys()) - db_categories
        assert unmatched == set(), (
            f"These mapping keys don't match any DB category string (apply_taxonomy "
            f"would silently skip them): {unmatched}"
        )


# ---------------------------------------------------------------------------
# apply_taxonomy — with realistic seed data
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.recap
class TestApplyTaxonomyWithSeedData:
    """
    End-to-end tests for POST /apply_taxonomy using the seeded dataset (52 articles,
    10 categories) and a recorded OpenAI fixture so results are deterministic.
    """

    def _set_mapping_in_session(self, client, mapping):
        with client.session_transaction() as sess:
            sess['category_mapping'] = mapping

    # -- happy path ----------------------------------------------------------

    def test_apply_returns_200_and_success_flash(
        self, seeded_authenticated_client, seeded_user, recap_app
    ):
        """POST /apply_taxonomy returns 200 and shows the success flash message."""
        fixture = _load_seed_fixture()
        mapping = _build_mapping_from_fixture(fixture)
        self._set_mapping_in_session(seeded_authenticated_client, mapping)

        response = seeded_authenticated_client.post('/apply_taxonomy', follow_redirects=True)
        assert response.status_code == 200
        assert b'updated successfully' in response.data

    def test_total_article_count_is_unchanged(
        self, seeded_authenticated_client, seeded_user, recap_app
    ):
        """Applying taxonomy must not create or delete any articles."""
        fixture = _load_seed_fixture()
        mapping = _build_mapping_from_fixture(fixture)
        self._set_mapping_in_session(seeded_authenticated_client, mapping)

        seeded_authenticated_client.post('/apply_taxonomy', follow_redirects=True)

        with recap_app.app_context():
            count = db.session.scalar(
                sa.select(sa.func.count(Article.id)).where(Article.user_id == seeded_user.id)
            )
        assert count == 52, f"Expected 52 articles after apply, got {count}"

    def test_no_old_categories_remain_after_apply(
        self, seeded_authenticated_client, seeded_user, recap_app
    ):
        """
        After apply, no article should still carry an old category that was
        supposed to be remapped to a different value.
        """
        fixture = _load_seed_fixture()
        mapping = _build_mapping_from_fixture(fixture)
        # Only care about categories that actually changed
        changed = {old: new for old, new in mapping.items() if old != new}
        self._set_mapping_in_session(seeded_authenticated_client, mapping)

        seeded_authenticated_client.post('/apply_taxonomy', follow_redirects=True)

        counts_after = _article_counts_by_category(recap_app, seeded_user.id)
        stale = {cat for cat in changed if cat in counts_after}
        assert stale == set(), (
            f"These old categories were NOT remapped — apply_taxonomy failed to "
            f"update them: {stale}"
        )

    def test_merged_categories_combine_article_counts(
        self, seeded_authenticated_client, seeded_user, recap_app
    ):
        """
        'Cooking Techniques' (2) and 'Culinary Arts' (1) both map to the same new
        category in the fixture. After apply the merged category should have 3 articles.
        The merged name is derived from the fixture so the test stays valid if the
        AI renames it (e.g. 'Gastronomy' vs 'Culinary Skills').
        """
        fixture = _load_seed_fixture()
        mapping = _build_mapping_from_fixture(fixture)

        # Derive the merged cooking category name from the fixture itself
        merged_name = mapping.get('Cooking Techniques')
        assert merged_name is not None, "Fixture must map 'Cooking Techniques'"
        assert mapping.get('Culinary Arts') == merged_name, (
            f"Expected 'Culinary Arts' to merge into '{merged_name}', "
            f"got '{mapping.get('Culinary Arts')}'"
        )

        self._set_mapping_in_session(seeded_authenticated_client, mapping)
        seeded_authenticated_client.post('/apply_taxonomy', follow_redirects=True)

        counts_after = _article_counts_by_category(recap_app, seeded_user.id)
        assert counts_after.get(merged_name) == 3, (
            f"Expected 3 articles under '{merged_name}' (merged from Cooking Techniques "
            f"+ Culinary Arts), got {counts_after.get(merged_name)}"
        )

    def test_identity_mapped_categories_preserve_count(
        self, seeded_authenticated_client, seeded_user, recap_app
    ):
        """
        Categories mapped to themselves (Artificial Intelligence: 27, Leadership: 10,
        Sports Science: 1) should keep their exact counts unchanged.
        """
        fixture = _load_seed_fixture()
        mapping = _build_mapping_from_fixture(fixture)
        identity = {old: new for old, new in mapping.items() if old == new}
        self._set_mapping_in_session(seeded_authenticated_client, mapping)

        seeded_authenticated_client.post('/apply_taxonomy', follow_redirects=True)

        counts_after = _article_counts_by_category(recap_app, seeded_user.id)
        for cat in identity:
            from tests.seed_data import SEED_CATEGORY_COUNTS
            expected = SEED_CATEGORY_COUNTS[cat]
            got = counts_after.get(cat, 0)
            assert got == expected, (
                f"'{cat}' should still have {expected} articles after apply, got {got}"
            )

    def test_session_mapping_is_cleared_after_apply(
        self, seeded_authenticated_client, seeded_user, recap_app
    ):
        """category_mapping must be removed from the session after a successful apply."""
        fixture = _load_seed_fixture()
        mapping = _build_mapping_from_fixture(fixture)
        self._set_mapping_in_session(seeded_authenticated_client, mapping)

        seeded_authenticated_client.post('/apply_taxonomy', follow_redirects=True)

        with seeded_authenticated_client.session_transaction() as sess:
            assert 'category_mapping' not in sess

    # -- rename sanity -------------------------------------------------------

    def test_renamed_category_article_count_matches_original(
        self, seeded_authenticated_client, seeded_user, recap_app
    ):
        """
        Single-source renames (e.g. Business Strategy → Strategic Management, count=2)
        should produce the same count under the new name.
        """
        fixture = _load_seed_fixture()
        mapping = _build_mapping_from_fixture(fixture)
        self._set_mapping_in_session(seeded_authenticated_client, mapping)

        seeded_authenticated_client.post('/apply_taxonomy', follow_redirects=True)

        counts_after = _article_counts_by_category(recap_app, seeded_user.id)
        from tests.seed_data import SEED_CATEGORY_COUNTS

        # Verify every 1-to-1 rename that didn't merge multiple sources
        new_category_sources = {}
        for old, new in mapping.items():
            new_category_sources.setdefault(new, []).append(old)

        for new_cat, old_cats in new_category_sources.items():
            if len(old_cats) == 1:  # pure rename, no merge
                old_cat = old_cats[0]
                if old_cat != new_cat:
                    expected = SEED_CATEGORY_COUNTS[old_cat]
                    got = counts_after.get(new_cat, 0)
                    assert got == expected, (
                        f"'{old_cat}' → '{new_cat}': expected {expected} articles, got {got}"
                    )
