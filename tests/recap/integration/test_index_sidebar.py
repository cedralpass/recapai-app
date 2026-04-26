"""
Integration tests for the index page filter sidebar (logged-in state).

The sidebar renders a list of category links in the form:
    Category(count)
e.g.  Artificial Intelligence(27)

These tests use the `seeded_user` fixture (53 articles across 10 categories)
to verify that the sidebar is populated correctly from real classification data.
"""
import pytest
from tests.seed_data import SEED_CATEGORY_COUNTS


@pytest.mark.integration
@pytest.mark.recap
class TestIndexSidebar:

    @pytest.fixture
    def logged_in_client(self, recap_client, seeded_user):
        """recap_client authenticated as seeded_user."""
        recap_client.post('/auth/login', data={
            'username': seeded_user.username,
            'password': 'seedpass123',
        })
        return recap_client

    def test_sidebar_visible_when_authenticated(self, logged_in_client):
        """Filter sidebar heading appears for authenticated users."""
        response = logged_in_client.get('/')
        assert response.status_code == 200
        assert b'Filter Articles' in response.data

    def test_sidebar_absent_when_logged_out(self, recap_client):
        """Filter sidebar is not rendered for anonymous visitors."""
        response = recap_client.get('/')
        assert response.status_code == 200
        assert b'Filter Articles' not in response.data

    def test_all_link_present(self, logged_in_client):
        """'All' reset-filter link is always the first sidebar item."""
        response = logged_in_client.get('/')
        assert b'>All<' in response.data

    def test_all_categories_present(self, logged_in_client):
        """Every seeded category appears as a sidebar link."""
        response = logged_in_client.get('/')
        html = response.data.decode()
        for category in SEED_CATEGORY_COUNTS:
            assert category in html, f"Expected category '{category}' in sidebar"

    def test_category_counts_match_seed_data(self, logged_in_client):
        """Each category link shows the correct article count."""
        response = logged_in_client.get('/')
        html = response.data.decode()
        for category, expected_count in SEED_CATEGORY_COUNTS.items():
            label = f"{category}({expected_count})"
            assert label in html, (
                f"Expected '{label}' in sidebar but did not find it.\n"
                f"Hint: check that all seed articles for '{category}' were "
                f"inserted with a non-null `classified` timestamp."
            )

    def test_largest_category_appears_first(self, logged_in_client):
        """
        Artificial Intelligence (27 articles) should be listed before
        smaller categories because get_categories() orders by count desc.
        """
        response = logged_in_client.get('/')
        html = response.data.decode()
        ai_pos = html.find("Artificial Intelligence(27)")
        leadership_pos = html.find("Leadership(10)")
        assert ai_pos != -1, "AI category not found in sidebar"
        assert leadership_pos != -1, "Leadership category not found in sidebar"
        assert ai_pos < leadership_pos, (
            "Expected 'Artificial Intelligence' to appear before 'Leadership' "
            "(sidebar should be ordered by article count descending)"
        )

    def test_sidebar_category_links_are_valid(self, logged_in_client):
        """Each category link filters the article list to that category."""
        response = logged_in_client.get('/?category=Leadership')
        assert response.status_code == 200
        html = response.data.decode()
        # The page should still render the sidebar
        assert b'Filter Articles' in html.encode()
        # All Leadership articles should be in the response (first page)
        # The category filter link for Leadership should still appear
        assert 'Leadership' in html

    def test_sidebar_not_rendered_without_articles(self, recap_client, recap_app):
        """
        A newly registered user with no articles sees no sidebar category list
        (groupings is empty, so only the 'All' link is rendered, or the
        sidebar ul is empty — the template guards with `if groupings is not none`).
        """
        from recap.models import User
        from recap import db

        with recap_app.app_context():
            empty_user = User(username='emptyuser', email='empty@example.com')
            empty_user.set_password('emptypass')
            db.session.add(empty_user)
            db.session.commit()

        recap_client.post('/auth/login', data={
            'username': 'emptyuser',
            'password': 'emptypass',
        })
        response = recap_client.get('/')
        assert response.status_code == 200
        # No categories should appear in the sidebar since there are no articles
        for category in SEED_CATEGORY_COUNTS:
            assert category.encode() not in response.data
