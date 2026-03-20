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
class TestProgressiveRelaxation:
    def test_reduces_n_on_infeasible(self, sample_recipes, mock_logger):
        """Request 5 with impossible hard constraints but feasible at 3, min_choices=1."""
        # Only 3 Italian recipes; require all selected to be Italian (<=0 non-Italian)
        # At N=5 this is infeasible (only 3 Italian), but at N=3 it works
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger, min_choices=1)
        # Require all selected are Italian: non-Italian == 0
        picker.add_keyword_constraint(italian, 0, "<=", exclude=True)
        result = picker.solve()
        assert len(result.recipes) == 3
        assert len(result.warnings) > 0
        assert "Reduced" in result.warnings[0]

    def test_fails_at_min_choices(self, sample_recipes, mock_logger):
        """Constraints infeasible even at min_choices raises RuntimeError."""
        # Require 8 Italian hard — impossible at any N since only 3 Italian
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger, min_choices=3)
        picker.add_keyword_constraint(italian, 8, ">=")
        with pytest.raises(RuntimeError, match="No solution found"):
            picker.solve()

    def test_no_reduction_when_feasible(self, sample_recipes, mock_logger):
        """Feasible at original N, no warnings, full count returned."""
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger, min_choices=1)
        result = picker.solve()
        assert len(result.recipes) == 5
        assert result.warnings == ()


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
