"""
Integration tests for the mobile bottom sheet category filter on the index page.

These cover:
- Old horizontal pill row is removed
- Bottom sheet markup (sheet, backdrop, JS) is present for authenticated users
- Filter trigger button in the "Your bookmarks" header
- Active-state rendering in both the trigger and the sheet rows
- Sheet is absent for anonymous users and users with no articles
"""

import pytest

from tests.seed_data import SEED_CATEGORY_COUNTS


@pytest.mark.integration
@pytest.mark.recap
class TestIndexBottomSheet:
    @pytest.fixture
    def logged_in_client(self, recap_client, seeded_user):
        recap_client.post(
            "/auth/login",
            data={"username": seeded_user.username, "password": "seedpass123"},
        )
        return recap_client

    # ------------------------------------------------------------------
    # Pill row removal
    # ------------------------------------------------------------------

    def test_pill_row_removed(self, logged_in_client):
        """The old horizontal-scroll pill row must not appear in the response."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        # The old container had these two classes together on a single element
        assert b"overflow-x-auto" not in response.data

    # ------------------------------------------------------------------
    # Bottom sheet structure
    # ------------------------------------------------------------------

    def test_bottom_sheet_present_when_authenticated(self, logged_in_client):
        """The filter sheet element is rendered for logged-in users with articles."""
        response = logged_in_client.get("/")
        assert b'id="filter-sheet"' in response.data

    def test_bottom_sheet_absent_when_logged_out(self, recap_client):
        """Anonymous visitors never see the bottom sheet."""
        response = recap_client.get("/")
        assert b'id="filter-sheet"' not in response.data

    def test_backdrop_present_when_authenticated(self, logged_in_client):
        """The semi-transparent backdrop overlay is rendered alongside the sheet."""
        response = logged_in_client.get("/")
        assert b'id="sheet-backdrop"' in response.data

    def test_sheet_heading(self, logged_in_client):
        """Sheet contains the 'Filter by category' heading."""
        response = logged_in_client.get("/")
        assert b"Filter by category" in response.data

    def test_js_open_close_functions_present(self, logged_in_client):
        """openSheet / closeSheet JS functions are included on the page."""
        response = logged_in_client.get("/")
        html = response.data.decode()
        assert "function openSheet()" in html
        assert "function closeSheet()" in html

    # ------------------------------------------------------------------
    # Filter trigger button
    # ------------------------------------------------------------------

    def test_filter_trigger_present_with_articles(self, logged_in_client):
        """The filter trigger button (calls openSheet) appears in the header."""
        response = logged_in_client.get("/")
        assert b"openSheet()" in response.data

    def test_filter_trigger_shows_all_when_no_category(self, logged_in_client):
        """Trigger label reads 'All' when no category query param is set."""
        response = logged_in_client.get("/")
        html = response.data.decode()
        # The span inside the trigger button should contain "All"
        assert ">All<" in html

    def test_filter_trigger_shows_active_category_name(self, logged_in_client):
        """Trigger label shows the selected category name when a filter is active."""
        response = logged_in_client.get("/?category=Artificial+Intelligence")
        html = response.data.decode()
        assert "Artificial Intelligence" in html

    def test_filter_trigger_absent_for_user_with_no_articles(self, recap_client, recap_app):
        """A user with no articles gets no filter trigger (groupings is empty)."""
        from recap import db
        from recap.models import User

        with recap_app.app_context():
            empty_user = User(username="noarticles", email="noarticles@example.com")
            empty_user.set_password("pass123")
            db.session.add(empty_user)
            db.session.commit()

        recap_client.post(
            "/auth/login",
            data={"username": "noarticles", "password": "pass123"},
        )
        response = recap_client.get("/")
        # The JS function is always included; check the trigger button itself is absent
        assert b'onclick="openSheet()"' not in response.data

    # ------------------------------------------------------------------
    # Sheet content — categories and counts
    # ------------------------------------------------------------------

    def test_all_option_present_in_sheet(self, logged_in_client):
        """'All' is the first selectable row inside the bottom sheet."""
        response = logged_in_client.get("/")
        html = response.data.decode()
        sheet_start = html.find('id="filter-sheet"')
        assert sheet_start != -1
        sheet_html = html[sheet_start:]
        assert ">All<" in sheet_html

    def test_all_seed_categories_in_sheet(self, logged_in_client):
        """Every seeded category appears as a row in the bottom sheet."""
        response = logged_in_client.get("/")
        html = response.data.decode()
        sheet_start = html.find('id="filter-sheet"')
        sheet_html = html[sheet_start:]
        for category in SEED_CATEGORY_COUNTS:
            assert category in sheet_html, f"Expected category '{category}' in bottom sheet"

    def test_category_counts_in_sheet(self, logged_in_client):
        """Each category row shows the correct article count."""
        response = logged_in_client.get("/")
        html = response.data.decode()
        sheet_start = html.find('id="filter-sheet"')
        sheet_html = html[sheet_start:]
        for category, expected_count in SEED_CATEGORY_COUNTS.items():
            assert (
                str(expected_count) in sheet_html
            ), f"Expected count {expected_count} for '{category}' in bottom sheet"

    # ------------------------------------------------------------------
    # Active state rendering
    # ------------------------------------------------------------------

    def test_active_category_row_highlighted_in_sheet(self, logged_in_client):
        """The selected category row carries the active highlight classes."""
        response = logged_in_client.get("/?category=Artificial+Intelligence")
        html = response.data.decode()
        sheet_start = html.find('id="filter-sheet"')
        sheet_html = html[sheet_start:]
        # Active row gets bg-blue-50 text-blue-700 font-semibold
        assert "bg-blue-50" in sheet_html
        # The active category name must appear near the highlight
        ai_pos = sheet_html.find("Artificial Intelligence")
        highlight_pos = sheet_html.find("bg-blue-50")
        assert ai_pos != -1 and highlight_pos != -1
        assert (
            abs(ai_pos - highlight_pos) < 200
        ), "Active highlight class should be on the same row as the category name"

    def test_all_row_highlighted_when_no_filter(self, logged_in_client):
        """The 'All' row has the active highlight when no category filter is set."""
        response = logged_in_client.get("/")
        html = response.data.decode()
        sheet_start = html.find('id="filter-sheet"')
        sheet_html = html[sheet_start:]
        # Find the All row and confirm bg-blue-50 precedes the first category row
        all_row_pos = sheet_html.find(">All<")
        first_category_row_pos = min(sheet_html.find(cat) for cat in SEED_CATEGORY_COUNTS if cat in sheet_html)
        highlight_pos = sheet_html.find("bg-blue-50")
        assert highlight_pos != -1, "Expected an active highlight in the sheet"
        assert highlight_pos < first_category_row_pos, "Expected the 'All' row to be highlighted, not a category row"
        assert highlight_pos < all_row_pos + 200, "Active highlight should be on the 'All' row"

    def test_inactive_category_rows_not_highlighted(self, logged_in_client):
        """Category rows that are not selected must not carry the active style."""
        response = logged_in_client.get("/?category=Artificial+Intelligence")
        html = response.data.decode()
        sheet_start = html.find('id="filter-sheet"')
        sheet_html = html[sheet_start:]
        # Leadership should appear in the sheet but not have bg-blue-50 on its row
        leadership_pos = sheet_html.find("Leadership")
        assert leadership_pos != -1
        # Check the 200 chars around Leadership's row link for the highlight class
        row_context = sheet_html[max(0, leadership_pos - 150) : leadership_pos + 50]
        assert "bg-blue-50" not in row_context, "Inactive 'Leadership' row should not have the active highlight class"
