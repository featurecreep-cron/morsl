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


class TestSoftConstraintWeight:
    """F3: Verify soft constraint weight tuning affects solver behavior."""

    def test_weight_10_soft_constraint_satisfied_when_feasible(self, sample_recipes, mock_logger):
        """Weight=10 soft constraint should be satisfied when the pool supports it."""
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 1, ">=", weight=10)
        result = picker.solve()
        assert len(result.recipes) == 5
        sel_italian = [r for r in result.recipes if 10 in r.keywords]
        assert len(sel_italian) >= 1
        assert result.relaxed_constraints == ()

    def test_explicit_weight_override_honored(self, sample_recipes, mock_logger):
        """Explicit weight value is passed through to RelaxedConstraint."""
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        # Impossible: require 8 Italian, only 3 exist
        picker.add_keyword_constraint(italian, 8, ">=", weight=15)
        result = picker.solve()
        assert len(result.relaxed_constraints) > 0
        assert result.relaxed_constraints[0].weight == 15

    def test_high_weight_resists_relaxation(self, sample_recipes, mock_logger):
        """Higher weight constraint resists relaxation more than lower weight."""
        italian = [r for r in sample_recipes if 10 in r.keywords]
        japanese = [r for r in sample_recipes if 40 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        # Low weight: want 5 Japanese (only 2 exist)
        picker.add_keyword_constraint(japanese, 5, ">=", weight=1)
        # High weight: want 2 Italian (3 exist, feasible)
        picker.add_keyword_constraint(italian, 2, ">=", weight=20)
        result = picker.solve()
        sel_italian = [r for r in result.recipes if 10 in r.keywords]
        assert len(sel_italian) >= 2  # High weight kept


class TestMinChoices:
    """F4: Verify min_choices range-based selection."""

    def test_min_choices_returns_fewer_when_constrained(self, sample_recipes, mock_logger):
        """With tight constraints, solver can return fewer than numrecipes."""
        # Only 3 Italian recipes exist. Require all selected to be Italian.
        italian = [r for r in sample_recipes if 10 in r.keywords]
        # Request 5 but accept as few as 1
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger, min_choices=1)
        # Hard constraint: only Italian recipes
        picker.add_keyword_constraint(italian, 0, "<=", exclude=True)
        result = picker.solve()
        # Should get exactly 3 (all Italian recipes)
        assert len(result.recipes) == 3
        assert all(10 in r.keywords for r in result.recipes)

    def test_min_choices_prefers_max(self, sample_recipes, mock_logger):
        """Without tight constraints, solver still returns numrecipes."""
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger, min_choices=1)
        result = picker.solve()
        assert len(result.recipes) == 5

    def test_min_choices_none_backward_compatible(self, sample_recipes, mock_logger):
        """min_choices=None behaves like == numrecipes."""
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger, min_choices=None)
        result = picker.solve()
        assert len(result.recipes) == 5

    def test_min_choices_generates_warning(self, sample_recipes, mock_logger):
        """Warning when fewer recipes returned than requested."""
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger, min_choices=1)
        picker.add_keyword_constraint(italian, 0, "<=", exclude=True)
        result = picker.solve()
        assert len(result.recipes) < 5
        assert any("Found" in w and "of 5" in w for w in result.warnings)


class TestRelaxedConstraintFields:
    """F5: Verify RelaxedConstraint carries operator and original_count."""

    def test_relaxed_constraint_has_operator(self, sample_recipes, mock_logger):
        """RelaxedConstraint includes the operator from the constraint."""
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 8, ">=", weight=100)
        result = picker.solve()
        assert len(result.relaxed_constraints) > 0
        rc = result.relaxed_constraints[0]
        assert rc.operator == ">="
        assert rc.original_count == 8

    def test_relaxed_constraint_lte_operator(self, sample_recipes, mock_logger):
        """RelaxedConstraint for <= operator."""
        # All but 2 recipes have been cooked — require at most 1 cooked (impossible)
        cooked = [r for r in sample_recipes if r.cookedon is not None]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_cookedon_constraints(cooked, 1, "<=", weight=50)
        result = picker.solve()
        # Should relax since most recipes are cooked
        for rc in result.relaxed_constraints:
            if rc.operator == "<=":
                assert rc.original_count == 1
                break

    def test_relaxed_constraint_custom_label(self, sample_recipes, mock_logger):
        """Custom label from add_constraint is preserved in RelaxedConstraint."""
        italian = [r for r in sample_recipes if 10 in r.keywords]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger)
        picker.add_keyword_constraint(italian, 8, ">=", weight=100, label="keyword:Italian")
        result = picker.solve()
        assert len(result.relaxed_constraints) > 0
        assert result.relaxed_constraints[0].label == "keyword:Italian"


class TestLockedRecipes:
    """Tests for the locked recipe parameter used in recipe swap."""

    def test_locked_recipes_always_selected(self, sample_recipes, mock_logger):
        locked = sample_recipes[:3]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger, locked=locked)
        result = picker.solve()
        selected_ids = {r.id for r in result.recipes}
        for r in locked:
            assert r.id in selected_ids

    def test_locked_with_all_slots_filled(self, sample_recipes, mock_logger):
        """Lock N-1 recipes, solve for N — exactly 1 free slot."""
        locked = sample_recipes[:4]
        picker = RecipePicker(sample_recipes, 5, logger=mock_logger, locked=locked)
        result = picker.solve()
        assert len(result.recipes) == 5
        locked_ids = {r.id for r in locked}
        selected_ids = {r.id for r in result.recipes}
        assert locked_ids.issubset(selected_ids)
        # Exactly one recipe is not from the locked set
        new_recipes = selected_ids - locked_ids
        assert len(new_recipes) == 1

    def test_locked_with_constraints(self, sample_recipes, mock_logger):
        """Locked recipes + constraints — solver respects both."""
        locked = sample_recipes[:2]  # Carbonara (Italian) and Tacos (Mexican)
        picker = RecipePicker(sample_recipes, 3, logger=mock_logger, locked=locked)
        # Require at least 1 Japanese recipe in the free slot
        japanese = [r for r in sample_recipes if 40 in r.keywords]
        picker.add_keyword_constraint(japanese, 1, ">=")
        result = picker.solve()
        selected_ids = {r.id for r in result.recipes}
        assert locked[0].id in selected_ids
        assert locked[1].id in selected_ids
        japanese_selected = [r for r in result.recipes if 40 in r.keywords]
        assert len(japanese_selected) >= 1

    def test_empty_locked_list(self, sample_recipes, mock_logger):
        """Empty locked list behaves like normal solve."""
        picker = RecipePicker(sample_recipes, 3, logger=mock_logger, locked=[])
        result = picker.solve()
        assert len(result.recipes) == 3
