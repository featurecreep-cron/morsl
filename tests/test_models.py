from __future__ import annotations

from datetime import datetime, timezone

from models import Book, Keyword, Recipe

from .conftest import make_recipe


class TestRecipeEquality:
    def test_same_id_equal(self):
        r1 = make_recipe(1, "A")
        r2 = make_recipe(1, "B")
        assert r1 == r2

    def test_different_id_not_equal(self):
        r1 = make_recipe(1, "A")
        r2 = make_recipe(2, "A")
        assert r1 != r2

    def test_set_deduplication(self):
        r1 = make_recipe(1, "A")
        r2 = make_recipe(1, "B")
        assert len({r1, r2}) == 1

    def test_hash_consistency(self):
        r1 = make_recipe(1, "A")
        r2 = make_recipe(1, "B")
        assert hash(r1) == hash(r2)


class TestRecipesWithKeyword:
    def test_filters_matching_keywords(self, sample_recipes):
        kw_italian = Keyword({"id": 10, "name": "Italian"})
        result = Recipe.recipesWithKeyword(sample_recipes, [kw_italian])
        assert all(10 in r.keywords for r in result)
        assert len(result) == 3  # Pasta Carbonara, Pizza, Lasagna

    def test_multiple_keywords(self, sample_recipes):
        kw_italian = Keyword({"id": 10, "name": "Italian"})
        kw_japanese = Keyword({"id": 40, "name": "Japanese"})
        result = Recipe.recipesWithKeyword(sample_recipes, [kw_italian, kw_japanese])
        assert len(result) == 5  # 3 Italian + 2 Japanese

    def test_no_matching_keywords(self, sample_recipes):
        kw_none = Keyword({"id": 999, "name": "Nonexistent"})
        result = Recipe.recipesWithKeyword(sample_recipes, [kw_none])
        assert len(result) == 0

    def test_empty_recipes(self):
        kw = Keyword({"id": 10, "name": "Italian"})
        result = Recipe.recipesWithKeyword([], [kw])
        assert len(result) == 0


class TestRecipesWithDate:
    def test_filter_after_date(self, sample_recipes):
        cutoff = datetime(2024, 5, 1, tzinfo=timezone.utc)
        result = Recipe.recipesWithDate(sample_recipes, "cookedon", cutoff, after=True)
        assert all(r.cookedon > cutoff for r in result)

    def test_filter_before_date(self, sample_recipes):
        cutoff = datetime(2024, 5, 1, tzinfo=timezone.utc)
        result = Recipe.recipesWithDate(sample_recipes, "cookedon", cutoff, after=False)
        assert all(r.cookedon < cutoff for r in result)

    def test_none_dates_excluded(self, sample_recipes):
        cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)
        result = Recipe.recipesWithDate(sample_recipes, "cookedon", cutoff, after=True)
        # Sushi and Fish & Chips have cookedon=None, should be excluded
        assert all(r.cookedon is not None for r in result)

    def test_createdon_filter(self, sample_recipes):
        cutoff = datetime(2023, 6, 1, tzinfo=timezone.utc)
        result = Recipe.recipesWithDate(sample_recipes, "createdon", cutoff, after=True)
        assert all(r.createdon > cutoff for r in result)


class TestRecipesWithRating:
    def test_positive_rating_gte(self, sample_recipes):
        result = Recipe.recipesWithRating(sample_recipes, 4)
        assert all(r.rating >= 4 for r in result)

    def test_negative_rating_lte(self, sample_recipes):
        result = Recipe.recipesWithRating(sample_recipes, -3)
        assert all(0 < r.rating <= 3 for r in result)

    def test_zero_rating(self, sample_recipes):
        result = Recipe.recipesWithRating(sample_recipes, 0)
        assert len(result) == len(sample_recipes)


class TestKeywordModel:
    def test_keyword_equality(self):
        k1 = Keyword({"id": 1, "name": "A"})
        k2 = Keyword({"id": 1, "name": "B"})
        assert k1 == k2

    def test_keyword_repr(self):
        k = Keyword({"id": 1, "name": "Italian"})
        assert "Italian" in repr(k)


class TestBookModel:
    def test_book_with_filter(self):
        b = Book({"id": 1, "name": "Favorites", "filter": {"id": 5}})
        assert b.filter == 5

    def test_book_without_filter(self):
        b = Book({"id": 1, "name": "Favorites"})
        assert b.filter is None
