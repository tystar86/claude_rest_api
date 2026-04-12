"""Unit tests for blog.utils (build_unique_slug) and api_views helpers (paginate, can_manage_tags)."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from blog.api_views import can_manage_tags, paginate
from blog.utils import build_unique_slug
from blog.models import Tag
from blog.serializers import TagSerializer


# ── build_unique_slug ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestBuildUniqueSlug:
    """Tests for the build_unique_slug utility."""

    def test_basic_slug_generation(self):
        """Converts a plain title to a lowercase hyphenated slug."""
        assert build_unique_slug(Tag, "Python Tutorial") == "python-tutorial"

    def test_collision_appends_number(self, db):
        """Appends -2 when the base slug already exists."""
        Tag.objects.create(name="Python", slug="python")
        assert build_unique_slug(Tag, "Python") == "python-2"

    def test_multiple_collisions_increment(self, db):
        """Keeps incrementing until a unique slug is found."""
        Tag.objects.create(name="Python", slug="python")
        Tag.objects.create(name="Python 2", slug="python-2")
        assert build_unique_slug(Tag, "Python") == "python-3"

    def test_excludes_current_instance(self, db):
        """Does not consider the instance being updated as a collision."""
        tag = Tag.objects.create(name="Python", slug="python")
        assert build_unique_slug(Tag, "Python", instance_id=tag.id) == "python"

    def test_empty_text_falls_back_to_item(self):
        """Falls back to 'item' when the source text is empty."""
        assert build_unique_slug(Tag, "") == "item"

    def test_none_text_falls_back_to_item(self):
        """Falls back to 'item' when the source text is None."""
        assert build_unique_slug(Tag, None) == "item"

    def test_slug_truncated_to_model_max_length(self):
        """Base slug is truncated to the model field's max_length."""
        long_title = "word " * 20  # Tag.slug max_length=50
        slug = build_unique_slug(Tag, long_title)
        assert len(slug) <= 50

    def test_explicit_max_length_overrides_model_field(self):
        """An explicit max_length parameter is respected over the model field."""
        slug = build_unique_slug(Tag, "a-fairly-long-title", max_length=10)
        assert len(slug) <= 10

    def test_collision_suffix_respects_max_length(self, db):
        """Slug with collision suffix never exceeds max_length."""
        Tag.objects.create(name="abcdefghij", slug="abcdefghij")
        slug = build_unique_slug(Tag, "abcdefghij", max_length=10)
        assert slug == "abcdefgh-2"
        assert len(slug) <= 10

    def test_many_collisions_truncate_base_for_longer_suffix(self, db):
        """As suffix grows (e.g. -10, -11), the base is trimmed further."""
        # Fill slugs up to -9 to force a two-digit suffix
        Tag.objects.create(name="abcdefghij", slug="abcdefghij")
        for n in range(2, 10):
            Tag.objects.create(name=f"abcdefghij-{n}", slug=f"abcdefgh-{n}")
        slug = build_unique_slug(Tag, "abcdefghij", max_length=10)
        assert slug == "abcdefg-10"
        assert len(slug) <= 10


# ── can_manage_tags ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCanManageTags:
    """Tests for the can_manage_tags permission helper."""

    def test_anonymous_user_cannot_manage(self):
        """AnonymousUser is denied tag management."""
        assert not can_manage_tags(AnonymousUser())

    def test_regular_user_cannot_manage(self, user):
        """A user with the default role cannot manage tags."""
        assert not can_manage_tags(user)

    def test_moderator_can_manage(self, moderator):
        """A moderator is allowed to manage tags."""
        assert can_manage_tags(moderator)

    def test_admin_can_manage(self, admin_user):
        """An admin is allowed to manage tags."""
        assert can_manage_tags(admin_user)


# ── paginate ───────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPaginate:
    """Tests for the paginate helper."""

    def _make_request(self, page="1"):
        """Return a GET request with the given page parameter."""
        factory = RequestFactory()
        return factory.get("/", {"page": page})

    def test_returns_required_keys(self, db):
        """Result contains count, total_pages, page, and results."""
        request = self._make_request()
        result = paginate(Tag.objects.none(), request, TagSerializer)
        assert set(result.keys()) == {"count", "total_pages", "page", "results"}

    def test_first_page_returns_up_to_ten_items(self, db):
        """Page 1 returns at most 10 results for 15 items."""
        for i in range(15):
            Tag.objects.create(name=f"Tag{i}", slug=f"tag{i}")
        request = self._make_request(page="1")
        result = paginate(Tag.objects.all(), request, TagSerializer)
        assert result["count"] == 15
        assert result["total_pages"] == 2
        assert result["page"] == 1
        assert len(result["results"]) == 10

    def test_second_page_returns_remainder(self, db):
        """Page 2 returns the remaining 5 items from a 15-item set."""
        for i in range(15):
            Tag.objects.create(name=f"Tag{i}", slug=f"tag{i}")
        request = self._make_request(page="2")
        result = paginate(Tag.objects.all(), request, TagSerializer)
        assert result["page"] == 2
        assert len(result["results"]) == 5

    def test_invalid_page_defaults_to_one(self, db):
        """Non-numeric page parameter silently falls back to page 1."""
        request = self._make_request(page="abc")
        result = paginate(Tag.objects.none(), request, TagSerializer)
        assert result["page"] == 1

    def test_empty_queryset(self, db):
        """An empty queryset returns count=0 and total_pages=1."""
        request = self._make_request()
        result = paginate(Tag.objects.none(), request, TagSerializer)
        assert result["count"] == 0
        assert result["total_pages"] == 1
        assert result["results"] == []
