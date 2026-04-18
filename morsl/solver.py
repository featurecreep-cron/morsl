from __future__ import annotations

import random

from pulp import LpMaximize, LpProblem, LpVariable, lpSum, value
from pulp.apis import PULP_CBC_CMD

from morsl.constants import SOLVER_RANDOM_SCALE, SOLVER_SLACK_EPSILON
from morsl.models import RelaxedConstraint, SolverResult


class RecipePicker:
    def __init__(self, recipes, numrecipes, logger=None, min_choices=None, locked=None):
        self.logger = logger
        self.recipes = recipes
        self.numrecipes = numrecipes
        self.min_choices = min_choices if min_choices is not None else numrecipes
        self._locked_ids = {r.id for r in (locked or [])}

        # Store constraint specs for replay during progressive relaxation
        self._constraint_specs = []
        # Store random coefficients so they stay consistent across rebuilds
        self._random_coeffs = {r.id: SOLVER_RANDOM_SCALE * random.random() for r in self.recipes}
        # O(1) recipe lookup by ID — avoids O(n) scans per constraint per rebuild
        self._recipe_by_id = {r.id: r for r in self.recipes}
        # Pre-computed set for O(1) membership in constraint application
        self._recipe_set = set(self.recipes)

        self._build_problem()

    def _build_problem(self):
        """Build (or rebuild) the LP problem with all stored constraints."""
        self.solver = LpProblem("RecipePicker", LpMaximize)
        self.recipe_vars = LpVariable.dicts("Recipe", [r.id for r in self.recipes], cat="Binary")
        self.solver += lpSum(self.recipe_vars.values()) >= self.min_choices
        self.solver += lpSum(self.recipe_vars.values()) <= self.numrecipes

        # Lock pre-selected recipes
        for rid in self._locked_ids:
            if rid in self.recipe_vars:
                self.solver += self.recipe_vars[rid] == 1

        # Soft constraint tracking
        self.soft_constraints = []
        self.numcriteria = 0

        # Replay all stored constraints
        for spec in self._constraint_specs:
            self._apply_constraint(**spec)

    def _apply_constraint(
        self,
        found_recipe_ids,
        count,
        operator,
        exclude,
        intersect_pool,
        label,
        upper_bound,
        weight,
    ):
        """Apply a single constraint to the current solver problem."""
        # Reconstruct recipe list from IDs via O(1) lookup
        id_set = set(found_recipe_ids)
        found_recipes = [self._recipe_by_id[rid] for rid in id_set if rid in self._recipe_by_id]

        if intersect_pool:
            found_recipes = list(self._recipe_set & set(found_recipes))
        if exclude:
            found_recipes = list(self._recipe_set - set(found_recipes))

        expr = lpSum(self.recipe_vars[i] for i in [r.id for r in found_recipes])

        if operator == "!=":
            raise ValueError(
                f"'!=' operator is not supported by linear programming "
                f"solvers. Use exclude=True with '>=' or '<=' instead. "
                f"(constraint: {label})"
            )

        if weight > 0:
            self._add_soft_constraint(expr, count, operator, weight, label, upper_bound)
        else:
            self._add_hard_constraint(expr, count, operator, label, upper_bound)

        self.numcriteria += 1

    def _add_hard_constraint(self, expr, count, operator, label, upper_bound):
        if operator == ">=":
            self.solver += expr >= count
        elif operator == "<=":
            self.solver += expr <= count
        elif operator == "==":
            self.solver += expr == count
        elif operator == "between":
            if upper_bound is None:
                raise ValueError("'between' operator requires 'upper_bound'")
            self.solver += expr >= count
            self.solver += expr <= upper_bound
        else:
            raise ValueError(f"Invalid constraint operator: {operator}")

    def _add_soft_constraint(self, expr, count, operator, weight, label, upper_bound):
        if operator == ">=":
            slack = LpVariable(f"slack_{label}_{len(self.soft_constraints)}", lowBound=0)
            self.solver += expr + slack >= count
            self.soft_constraints.append((slack, weight, label, operator, count))
        elif operator == "<=":
            slack = LpVariable(f"slack_{label}_{len(self.soft_constraints)}", lowBound=0)
            self.solver += expr - slack <= count
            self.soft_constraints.append((slack, weight, label, operator, count))
        elif operator == "==":
            slack_pos = LpVariable(f"slack_{label}_{len(self.soft_constraints)}_pos", lowBound=0)
            slack_neg = LpVariable(f"slack_{label}_{len(self.soft_constraints)}_neg", lowBound=0)
            self.solver += expr + slack_pos - slack_neg == count
            self.soft_constraints.append((slack_pos, weight, label, operator, count))
            self.soft_constraints.append((slack_neg, weight, label, operator, count))
        elif operator == "between":
            if upper_bound is None:
                raise ValueError("'between' operator requires 'upper_bound'")
            slack_lo = LpVariable(f"slack_{label}_{len(self.soft_constraints)}_lo", lowBound=0)
            slack_hi = LpVariable(f"slack_{label}_{len(self.soft_constraints)}_hi", lowBound=0)
            self.solver += expr + slack_lo >= count
            self.solver += expr - slack_hi <= upper_bound
            self.soft_constraints.append((slack_lo, weight, label, ">=", count))
            self.soft_constraints.append((slack_hi, weight, label, "<=", upper_bound))
        else:
            raise ValueError(f"Invalid constraint operator: {operator}")

    def add_constraint(
        self,
        found_recipes,
        count,
        operator,
        *,
        exclude=False,
        intersect_pool=False,
        label="constraint",
        upper_bound=None,
        weight=0,
    ):
        """Generic method to add a constraint to the solver.

        Args:
            found_recipes: Recipes matching the constraint condition.
            count: Number threshold for the constraint.
            operator: One of '>=', '<=', '==', '!=', 'between'.
            exclude: If True, invert the recipe set (pool minus found).
            intersect_pool: If True, intersect found_recipes with self.recipes first.
            label: Description for logging.
            upper_bound: Required when operator is 'between'; sets the upper limit.
            weight: 0 for hard constraint; >0 for soft constraint (penalty weight).
        """
        found_recipe_ids = [r.id for r in found_recipes]
        spec = {
            "found_recipe_ids": found_recipe_ids,
            "count": count,
            "operator": operator,
            "exclude": exclude,
            "intersect_pool": intersect_pool,
            "label": label,
            "upper_bound": upper_bound,
            "weight": weight,
        }
        self._constraint_specs.append(spec)
        self._apply_constraint(**spec)

        self.logger.debug(
            f"Added {label} constraint {operator} {count}.  "
            f"Found {len(found_recipes)} matching recipes."
        )

    def add_food_constraint(self, found_recipes, numrecipes, operator, exclude=False, **kwargs):
        kwargs.setdefault("label", "food")
        self.add_constraint(
            found_recipes,
            numrecipes,
            operator,
            exclude=exclude,
            intersect_pool=True,
            **kwargs,
        )

    def add_book_constraint(self, found_recipes, numrecipes, operator, exclude=False, **kwargs):
        kwargs.setdefault("label", "book")
        self.add_constraint(
            found_recipes,
            numrecipes,
            operator,
            exclude=exclude,
            intersect_pool=True,
            **kwargs,
        )

    def add_keyword_constraint(self, found_recipes, numrecipes, operator, exclude=False, **kwargs):
        kwargs.setdefault("label", "keyword")
        self.add_constraint(found_recipes, numrecipes, operator, exclude=exclude, **kwargs)

    def add_rating_constraints(self, found_recipes, numrecipes, operator, exclude=False, **kwargs):
        kwargs.setdefault("label", "rating")
        self.add_constraint(found_recipes, numrecipes, operator, exclude=exclude, **kwargs)

    def add_createdon_constraints(
        self, found_recipes, numrecipes, operator, exclude=False, **kwargs
    ):
        kwargs.setdefault("label", "createdon")
        self.add_constraint(found_recipes, numrecipes, operator, exclude=exclude, **kwargs)

    def add_cookedon_constraints(
        self, found_recipes, numrecipes, operator, exclude=False, **kwargs
    ):
        kwargs.setdefault("label", "cookedon")
        self.add_constraint(found_recipes, numrecipes, operator, exclude=exclude, **kwargs)

    def _build_objective(self):
        """Build objective: maximize variety + penalize soft constraint violations."""
        obj = lpSum(self._random_coeffs[r.id] * self.recipe_vars[r.id] for r in self.recipes)
        for slack_var, w, _label, _op, _count in self.soft_constraints:
            obj -= w * slack_var
        self.solver += obj

    def solve(self) -> SolverResult:
        self.logger.debug(
            f"Solving to choose {self.numrecipes} with {self.numcriteria} unique criteria."
        )
        debug = self.logger.loglevel == 10

        self._build_problem()
        self._build_objective()
        self.solver.solve(PULP_CBC_CMD(msg=debug))

        if self.solver.status != 1:
            self.logger.warning(
                "No solution found at %d recipes — adjustment of criteria required.",
                self.numrecipes,
            )
            raise RuntimeError("No solution found.")

        # Collect relaxed constraints
        relaxed = []
        for slack_var, w, label, op, count in self.soft_constraints:
            sv = value(slack_var) or 0.0
            if sv > SOLVER_SLACK_EPSILON:
                relaxed.append(
                    RelaxedConstraint(
                        label=label,
                        slack_value=sv,
                        weight=w,
                        operator=op,
                        original_count=count,
                    )
                )

        selected = [r for r in self.recipes if (value(self.recipe_vars[r.id]) or 0) >= 0.5]
        self.logger.info(f"Solver selected {len(selected)} recipes: {[r.name for r in selected]}")
        warnings = []
        if len(selected) < self.numrecipes:
            warnings.append(f"Found {len(selected)} of {self.numrecipes} requested recipes")
        return SolverResult(
            recipes=tuple(selected),
            requested_count=self.numrecipes,
            constraint_count=self.numcriteria,
            relaxed_constraints=tuple(relaxed),
            warnings=tuple(warnings),
            status="optimal",
        )
