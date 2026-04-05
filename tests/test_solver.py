from __future__ import annotations

import pytest

from morsl.models import RelaxedConstraint, SolverResult, make_recipe
from morsl.solver import RecipePicker


class TestRecipePickerBasic:
    def test_selects_correct_number(self, sample_recipes, mock_logger):
        picker = RecipePicker(sample_recipes, 3, logger=mock_logger)
        result = picker.solve()
        assert isinstance(result, SolverResult)
        assert len(result.recipes) == 3

    def test_selects_all_recipes(self, sample_recipes, mock_logger):
        picker = RecipePicker(sample_recipes, len(sample_recipes), logger=mock_logger)
        result = picker.solve()
        assert len(result.recipes) == len(sample_recipes)

    def test_selects_one_recipe(self, sample_recipes, mock_logger):
        picker = RecipePicker(sample_recipes, 1, logger=mock_logger)
        result = picker.solve()
        assert len(result.recipes) == 1

    def test_infeasible_raises(self, sample_recipes, mock_logger):
        picker = RecipePicker(sample_recipes, len(sample_recipes) + 1, logger=mock_logger)
        with pytest.raises(RuntimeError, match="No solution found"):
            picker.solve()


class TestConstraintOperators:
    def test_lte_constraint(self, sample_recipes, mock_logger):
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 1, "<=")
        result = picker.solve()
        selected_italian = [r for r in result.recipes if 10 in r.keywords]
        assert len(selected_italian) <= 1

    def test_eq_constraint(self, sample_recipes, mock_logger):
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 2, "==")
        result = picker.solve()
        selected_italian = [r for r in result.recipes if 10 in r.keywords]
        assert len(selected_italian) == 2

    def test_between_constraint(self, sample_recipes, mock_logger):
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 1, "between", upper_bound=2)
        result = picker.solve()
        selected_italian = [r for r in result.recipes if 10 in r.keywords]
        assert 1 <= len(selected_italian) <= 2

    def test_between_missing_upper_bound(self, sample_recipes, mock_logger):
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        with pytest.raises(ValueError, match="upper_bound"):
            picker.add_keyword_constraint(sample_recipes[:3], 1, "between")

    def test_invalid_operator(self, sample_recipes, mock_logger):
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        with pytest.raises(ValueError, match="Invalid constraint operator"):
            picker.add_keyword_constraint(sample_recipes[:3], 1, ">>")


class TestExcludeAndIntersect:
    def test_exclude_constraint(self, sample_recipes, mock_logger):
        """exclude=True inverts the set: Italian recipes become non-Italian for the constraint."""
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        # exclude=True flips italian→non-italian; require >= 3 non-Italian
        picker.add_keyword_constraint(italian, 3, ">=", exclude=True)
        result = picker.solve()
        selected_non_italian = [r for r in result.recipes if 10 not in r.keywords]
        assert len(selected_non_italian) >= 3

    def test_intersect_pool_food(self, sample_recipes, mock_logger):
        # food/book constraints intersect with the recipe pool first
        extra_recipe = make_recipe(
            {
                "id": 999,
                "name": "Unknown",
                "description": "",
                "new": False,
                "servings": 1,
                "keywords": [],
                "rating": 0,
                "last_cooked": None,
                "created_at": "2024-01-01T12:00:00+00:00",
            }
        )
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        # extra_recipe is NOT in the picker pool, so intersect removes it
        picker.add_food_constraint([extra_recipe, *sample_recipes[:2]], 1, ">=")
        result = picker.solve()
        assert len(result.recipes) == 5

    def test_multiple_constraints(self, sample_recipes, mock_logger):
        italian = [r for r in sample_recipes if 10 in r.keywords]
        japanese = [r for r in sample_recipes if 40 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 1, ">=")
        picker.add_keyword_constraint(japanese, 1, ">=")
        result = picker.solve()
        sel_italian = [r for r in result.recipes if 10 in r.keywords]
        sel_japanese = [r for r in result.recipes if 40 in r.keywords]
        assert len(sel_italian) >= 1
        assert len(sel_japanese) >= 1


@pytest.mark.slow
class TestSolverResult:
    def test_result_has_correct_requested_count(self, sample_recipes, mock_logger):
        picker = RecipePicker(sample_recipes, 3, logger=mock_logger)
        result = picker.solve()
        assert result.requested_count == 3

    def test_result_has_correct_constraint_count(self, sample_recipes, mock_logger):
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 1, ">=")
        picker.add_keyword_constraint(italian, 4, "<=")
        result = picker.solve()
        assert result.constraint_count == 2

    def test_result_metadata_defaults(self, sample_recipes, mock_logger):
        picker = RecipePicker(sample_recipes, 3, logger=mock_logger)
        result = picker.solve()
        assert result.status == "optimal"
        assert result.relaxed_constraints == ()
        assert result.warnings == ()


@pytest.mark.slow
class TestSoftConstraints:
    def test_soft_constraint_relaxes(self, sample_recipes, mock_logger):
        """Impossible soft constraint (weight>0) gets relaxed; solver succeeds."""
        # Only 3 Italian recipes exist; require >= 8 with soft constraint
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 8, ">=", weight=100)
        result = picker.solve()
        assert len(result.recipes) == 5
        assert len(result.relaxed_constraints) > 0
        assert all(isinstance(rc, RelaxedConstraint) for rc in result.relaxed_constraints)

    def test_soft_constraint_not_relaxed_when_feasible(self, sample_recipes, mock_logger):
        """Feasible soft constraint stays satisfied; relaxed_constraints is empty."""
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 1, ">=", weight=100)
        result = picker.solve()
        assert len(result.recipes) == 5
        assert result.relaxed_constraints == ()

    def test_mixed_hard_and_soft(self, sample_recipes, mock_logger):
        """Hard constraint satisfied, soft constraint relaxed when needed."""
        italian = [r for r in sample_recipes if 10 in r.keywords]
        japanese = [r for r in sample_recipes if 40 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        # Hard: at least 1 Japanese (feasible)
        picker.add_keyword_constraint(japanese, 1, ">=", weight=0)
        # Soft: at least 8 Italian (impossible, only 3 exist)
        picker.add_keyword_constraint(italian, 8, ">=", weight=100)
        result = picker.solve()
        assert len(result.recipes) == 5
        sel_japanese = [r for r in result.recipes if 40 in r.keywords]
        assert len(sel_japanese) >= 1
        assert len(result.relaxed_constraints) > 0


@pytest.mark.slow
class TestConstraintInfeasibility:
    def test_hard_constraint_infeasible_raises(self, sample_recipes, mock_logger):
        """Hard constraints that can't be satisfied raise RuntimeError."""
        # Only 3 Italian recipes; require all 5 selected to be Italian — impossible
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 0, "<=", exclude=True)
        with pytest.raises(RuntimeError, match="No solution found"):
            picker.solve()

    def test_soft_constraint_relaxes_on_infeasible(self, sample_recipes, mock_logger):
        """Soft constraints relax when infeasible — still returns full recipe count."""
        # Only 3 Italian recipes; request 5 Italian as soft constraint
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 5, ">=", weight=50)
        result = picker.solve()
        assert len(result.recipes) == 5
        assert len(result.relaxed_constraints) > 0

    def test_hard_constraint_impossible_count(self, sample_recipes, mock_logger):
        """Require 8 Italian hard — impossible since only 3 Italian."""
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 8, ">=")
        with pytest.raises(RuntimeError, match="No solution found"):
            picker.solve()

    def test_feasible_no_relaxation(self, sample_recipes, mock_logger):
        """Feasible constraints produce no relaxation and full count."""
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        result = picker.solve()
        assert len(result.recipes) == 5
        assert result.warnings == ()
        assert result.relaxed_constraints == ()


class TestBackwardCompatibility:
    def test_no_weight_field_identical(self, sample_recipes, mock_logger):
        """Constraints without weight behave exactly as before (hard)."""
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 2, ">=")
        result = picker.solve()
        selected_italian = [r for r in result.recipes if 10 in r.keywords]
        assert len(selected_italian) >= 2
        assert result.relaxed_constraints == ()

    def test_no_min_choices_identical(self, sample_recipes, mock_logger):
        """No min_choices means no progressive relaxation — infeasible raises immediately."""
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 8, ">=")
        with pytest.raises(RuntimeError, match="No solution found"):
            picker.solve()


class TestDateConstraints:
    """Test add_cookedon_constraints and add_createdon_constraints."""

    def test_cookedon_gte_constraint(self, sample_recipes, mock_logger):
        """cookedon constraint with >= selects recently-cooked recipes."""
        cooked = [r for r in sample_recipes if r.cookedon is not None]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_cookedon_constraints(cooked, 2, ">=")
        result = picker.solve()
        sel_cooked = [r for r in result.recipes if r.cookedon is not None]
        assert len(sel_cooked) >= 2

    def test_cookedon_lte_constraint(self, sample_recipes, mock_logger):
        """cookedon constraint with <= caps cooked recipes."""
        cooked = [r for r in sample_recipes if r.cookedon is not None]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        # 8 of 10 recipes have been cooked; allow at most 4 in selection of 5
        picker.add_cookedon_constraints(cooked, 4, "<=")
        result = picker.solve()
        sel_cooked = [r for r in result.recipes if r.cookedon is not None]
        assert len(sel_cooked) <= 4

    def test_createdon_gte_constraint(self, sample_recipes, mock_logger):
        """createdon constraint with >= selects recipes created in date range."""
        from datetime import datetime, timezone

        cutoff = datetime(2023, 5, 1, tzinfo=timezone.utc)
        recent = [r for r in sample_recipes if r.createdon and r.createdon >= cutoff]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_createdon_constraints(recent, 2, ">=")
        result = picker.solve()
        sel_recent = [r for r in result.recipes if r.createdon and r.createdon >= cutoff]
        assert len(sel_recent) >= 2

    def test_cookedon_exclude(self, sample_recipes, mock_logger):
        """exclude=True inverts cooked set — constrains never-cooked recipes."""
        cooked = [r for r in sample_recipes if r.cookedon is not None]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        # exclude=True: constraint applies to never-cooked recipes
        picker.add_cookedon_constraints(cooked, 1, ">=", exclude=True)
        result = picker.solve()
        sel_uncooked = [r for r in result.recipes if r.cookedon is None]
        assert len(sel_uncooked) >= 1

    def test_cookedon_uses_correct_label(self, sample_recipes, mock_logger):
        """Verify the constraint label is 'cookedon'."""
        cooked = [r for r in sample_recipes if r.cookedon is not None]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_cookedon_constraints(cooked, 1, ">=")
        assert picker._constraint_specs[-1]["label"] == "cookedon"

    def test_createdon_uses_correct_label(self, sample_recipes, mock_logger):
        """Verify the constraint label is 'createdon'."""
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_createdon_constraints(sample_recipes[:3], 1, ">=")
        assert picker._constraint_specs[-1]["label"] == "createdon"

    def test_date_constraints_no_intersect_pool(self, sample_recipes, mock_logger):
        """Date constraints use intersect_pool=False (unlike food/book)."""
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_cookedon_constraints(sample_recipes[:3], 1, ">=")
        assert picker._constraint_specs[-1]["intersect_pool"] is False

    def test_cookedon_soft_constraint(self, sample_recipes, mock_logger):
        """Cookedon constraint with weight > 0 behaves as soft constraint."""
        cooked = [r for r in sample_recipes if r.cookedon is not None]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        # Impossible: require 10 cooked recipes in selection of 5
        picker.add_cookedon_constraints(cooked, 10, ">=", weight=50)
        result = picker.solve()
        assert len(result.recipes) == 5
        assert len(result.relaxed_constraints) > 0

    def test_cookedon_eq_constraint(self, sample_recipes, mock_logger):
        """cookedon constraint with == selects exact count of cooked recipes."""
        cooked = [r for r in sample_recipes if r.cookedon is not None]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_cookedon_constraints(cooked, 3, "==")
        result = picker.solve()
        sel_cooked = [r for r in result.recipes if r.cookedon is not None]
        assert len(sel_cooked) == 3

    def test_cookedon_between_constraint(self, sample_recipes, mock_logger):
        """cookedon constraint with 'between' bounds cooked recipe count."""
        cooked = [r for r in sample_recipes if r.cookedon is not None]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_cookedon_constraints(cooked, 2, "between", upper_bound=4)
        result = picker.solve()
        sel_cooked = [r for r in result.recipes if r.cookedon is not None]
        assert 2 <= len(sel_cooked) <= 4

    def test_createdon_lte_constraint(self, sample_recipes, mock_logger):
        """createdon constraint with <= caps recipes created in range."""
        from datetime import datetime, timezone

        cutoff = datetime(2023, 5, 1, tzinfo=timezone.utc)
        recent = [r for r in sample_recipes if r.createdon and r.createdon >= cutoff]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        # At most 3 of the selection should be from after May 2023
        picker.add_createdon_constraints(recent, 3, "<=")
        result = picker.solve()
        sel_recent = [r for r in result.recipes if r.createdon and r.createdon >= cutoff]
        assert len(sel_recent) <= 3

    def test_createdon_eq_constraint(self, sample_recipes, mock_logger):
        """createdon constraint with == selects exact count from date range."""
        from datetime import datetime, timezone

        cutoff = datetime(2023, 5, 1, tzinfo=timezone.utc)
        recent = [r for r in sample_recipes if r.createdon and r.createdon >= cutoff]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_createdon_constraints(recent, 3, "==")
        result = picker.solve()
        sel_recent = [r for r in result.recipes if r.createdon and r.createdon >= cutoff]
        assert len(sel_recent) == 3

    def test_createdon_between_constraint(self, sample_recipes, mock_logger):
        """createdon constraint with 'between' bounds count in range."""
        from datetime import datetime, timezone

        cutoff = datetime(2023, 5, 1, tzinfo=timezone.utc)
        recent = [r for r in sample_recipes if r.createdon and r.createdon >= cutoff]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_createdon_constraints(recent, 1, "between", upper_bound=3)
        result = picker.solve()
        sel_recent = [r for r in result.recipes if r.createdon and r.createdon >= cutoff]
        assert 1 <= len(sel_recent) <= 3

    def test_createdon_exclude(self, sample_recipes, mock_logger):
        """createdon with exclude=True constrains recipes NOT in the date range."""
        from datetime import datetime, timezone

        cutoff = datetime(2023, 5, 1, tzinfo=timezone.utc)
        recent = [r for r in sample_recipes if r.createdon and r.createdon >= cutoff]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        # exclude=True: constraint applies to recipes created BEFORE cutoff
        picker.add_createdon_constraints(recent, 2, ">=", exclude=True)
        result = picker.solve()
        sel_old = [r for r in result.recipes if r.createdon and r.createdon < cutoff]
        assert len(sel_old) >= 2

    def test_createdon_soft_constraint(self, sample_recipes, mock_logger):
        """createdon with weight > 0 relaxes when impossible."""
        from datetime import datetime, timezone

        cutoff = datetime(2023, 5, 1, tzinfo=timezone.utc)
        recent = [r for r in sample_recipes if r.createdon and r.createdon >= cutoff]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        # Impossible: require 10 recent recipes in selection of 5
        picker.add_createdon_constraints(recent, 10, ">=", weight=50)
        result = picker.solve()
        assert len(result.recipes) == 5
        assert len(result.relaxed_constraints) > 0

    def test_between_requires_upper_bound(self, sample_recipes, mock_logger):
        """'between' operator without upper_bound raises ValueError."""
        cooked = [r for r in sample_recipes if r.cookedon is not None]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        with pytest.raises(ValueError, match="upper_bound"):
            picker.add_cookedon_constraints(cooked, 2, "between")
