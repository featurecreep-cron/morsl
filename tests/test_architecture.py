"""Lint tests for architectural constraints.

Ensures boundaries are maintained:
- Layer invariant: routes → services → core → foundation
- requests only in tandoor_api.py and proxy.py
- TandoorAPI instantiation only in service modules
- No token exposure in log statements
- Frozen dataclasses (once domain models are migrated)
- No direct file writes in route modules
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "morsl"
SERVICES = SRC / "services"
ROUTES = SRC / "app" / "api" / "routes"


def _python_files(directory: Path, exclude: set[str] | None = None) -> list[Path]:
    """All .py files in a directory, excluding specified filenames."""
    exclude = exclude or set()
    return [p for p in directory.glob("*.py") if p.name not in exclude and p.name != "__init__.py"]


def _all_source_files() -> list[Path]:
    """All .py files in morsl/ recursively, excluding __init__.py."""
    return [p for p in SRC.rglob("*.py") if p.name != "__init__.py"]


class TestLayerViolation:
    """No upward layer imports.

    Layer hierarchy (top to bottom):
    - Layer 4 (API): app/main.py, app/api/routes/*.py,
      app/api/dependencies.py, app/api/models.py
    - Layer 3 (Services): services/*.py
    - Layer 2 (Core): solver.py, tandoor_api.py
    - Layer 1 (Foundation): models.py, constants.py, utils.py,
      app/config.py
    """

    # Map module import paths to layers
    _MODULE_LAYERS: dict[str, int] = {
        # Foundation = 1
        "morsl.models": 1,
        "morsl.constants": 1,
        "morsl.utils": 1,
        "morsl.app.config": 1,
        # Core = 2
        "morsl.solver": 2,
        "morsl.tandoor_api": 2,
    }

    # Services are all layer 3
    _SERVICE_PREFIX = "morsl.services."

    # API layer = 4
    _API_MODULES = {
        "morsl.app.main",
        "morsl.app.api.dependencies",
        "morsl.app.api.models",
    }
    _API_ROUTE_PREFIX = "morsl.app.api.routes."

    def _get_layer(self, module_path: str) -> int | None:
        if module_path in self._MODULE_LAYERS:
            return self._MODULE_LAYERS[module_path]
        if module_path.startswith(self._SERVICE_PREFIX):
            return 3
        if module_path in self._API_MODULES or module_path.startswith(self._API_ROUTE_PREFIX):
            return 4
        return None

    def _file_to_module(self, path: Path) -> str:
        """Convert file path to module import path."""
        rel = path.relative_to(SRC.parent)
        parts = rel.with_suffix("").parts
        return ".".join(parts)

    @staticmethod
    def _type_checking_lines(tree: ast.Module) -> set[int]:
        """Collect line numbers of imports inside TYPE_CHECKING."""
        lines: set[int] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                for child in ast.walk(node):
                    if isinstance(child, (ast.Import, ast.ImportFrom)):
                        lines.add(child.lineno)
        return lines

    @staticmethod
    def _extract_morsl_imports(tree, tc_lines):
        """Yield (lineno, module_name) for all morsl imports outside TYPE_CHECKING."""
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if node.lineno in tc_lines:
                continue
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("morsl.")
            ):
                yield node.lineno, node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("morsl."):
                        yield node.lineno, alias.name

    def test_no_upward_imports(self):
        """Modules must not import from a layer above them."""
        violations = []
        for path in _all_source_files():
            src_module = self._file_to_module(path)
            src_layer = self._get_layer(src_module)
            if src_layer is None:
                continue

            tree = ast.parse(path.read_text())
            tc_lines = self._type_checking_lines(tree)

            for lineno, imported_module in self._extract_morsl_imports(tree, tc_lines):
                target_layer = self._get_layer(imported_module)
                if target_layer is not None and target_layer > src_layer:
                    violations.append(
                        f"{path.name}:{lineno} imports {imported_module} "
                        f"(layer {target_layer}) from layer {src_layer}"
                    )
        assert not violations, "Upward layer imports detected:\n" + "\n".join(violations)


class TestRequestsConstraint:
    """import requests only in tandoor_api.py and proxy.py."""

    _ALLOWED = {"tandoor_api.py", "proxy.py"}

    def test_requests_only_in_allowed_files(self):
        violations = []
        for path in _all_source_files():
            if path.name in self._ALLOWED:
                continue
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "requests":
                            violations.append(f"{path.name}:{node.lineno}")
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and (node.module == "requests" or node.module.startswith("requests."))
                ):
                    violations.append(f"{path.name}:{node.lineno}")
        assert not violations, (
            "requests imported outside allowed files "
            f"({', '.join(self._ALLOWED)}):\n" + "\n".join(violations)
        )


class TestHttpxConstraint:
    """import httpx only in settings route and proxy."""

    _ALLOWED = {"settings.py", "proxy.py"}

    def test_httpx_only_in_allowed_files(self):
        violations = []
        for path in _all_source_files():
            if path.name in self._ALLOWED:
                continue
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "httpx":
                            violations.append(f"{path.name}:{node.lineno}")
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and (node.module == "httpx" or node.module.startswith("httpx."))
                ):
                    violations.append(f"{path.name}:{node.lineno}")
        assert not violations, (
            "httpx imported outside allowed files "
            f"({', '.join(self._ALLOWED)}):\n" + "\n".join(violations)
        )


class TestTandoorAPIInstantiation:
    """TandoorAPI() only in service modules."""

    _ALLOWED_DIRS = {SERVICES}

    def test_no_tandoor_api_in_routes(self):
        """Route modules must not instantiate TandoorAPI."""
        violations = []
        for path in _python_files(ROUTES):
            source = path.read_text()
            if "TandoorAPI(" in source:
                for i, line in enumerate(source.splitlines(), 1):
                    if "TandoorAPI(" in line:
                        violations.append(f"{path.name}:{i}")
        assert not violations, "TandoorAPI instantiated in route module:\n" + "\n".join(violations)


class TestTokenExposure:
    """No f-strings containing 'token' in logger calls."""

    _TOKEN_IN_FSTRING = re.compile(
        r"""
        \.(?:debug|info|warning|error|critical)\s*\(
        \s*f["'].*token
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    def test_no_token_in_log_fstrings(self):
        violations = []
        for path in _all_source_files():
            for i, line in enumerate(path.read_text().splitlines(), 1):
                if self._TOKEN_IN_FSTRING.search(line):
                    # Allow noqa suppression
                    if "# noqa: token-log" in line:
                        continue
                    violations.append(f"{path.name}:{i}: {line.strip()}")
        assert not violations, (
            "Token referenced in log f-string "
            "(risk of credential exposure):\n" + "\n".join(violations)
        )


class TestFrozenDataclasses:
    """All dataclasses should be frozen unless in _MUTABLE_ALLOWED."""

    # Intentionally mutable dataclasses with justification
    _MUTABLE_ALLOWED = {
        # GenerationStatus is a state machine tracking progress
        ("generation_service.py", "GenerationStatus"),
        # WeeklyGenerationStatus — same pattern
        ("weekly_generation_service.py", "WeeklyGenerationStatus"),
    }

    def test_dataclasses_are_frozen(self):
        violations = []
        for path in _all_source_files():
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        func = decorator.func
                        if isinstance(func, ast.Name) and func.id == "dataclass":
                            frozen = any(
                                kw.arg == "frozen"
                                and isinstance(kw.value, ast.Constant)
                                and kw.value.value is True
                                for kw in decorator.keywords
                            )
                            if (
                                not frozen
                                and (
                                    path.name,
                                    node.name,
                                )
                                not in self._MUTABLE_ALLOWED
                            ):
                                violations.append(
                                    f"{path.name}:{node.lineno} "
                                    f"class {node.name} — "
                                    f"@dataclass without frozen=True"
                                )
                    elif isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                        if (
                            path.name,
                            node.name,
                        ) not in self._MUTABLE_ALLOWED:
                            violations.append(
                                f"{path.name}:{node.lineno} "
                                f"class {node.name} — "
                                f"@dataclass without frozen=True"
                            )
        assert not violations, (
            "Dataclass not frozen (add frozen=True or add to "
            "_MUTABLE_ALLOWED with justification):\n" + "\n".join(violations)
        )


class TestSyncCoreModules:
    """solver.py and tandoor_api.py never import asyncio."""

    _SYNC_MODULES = {"solver.py", "tandoor_api.py", "models.py"}

    def test_no_asyncio_in_sync_core(self):
        violations = []
        for path in SRC.glob("*.py"):
            if path.name not in self._SYNC_MODULES:
                continue
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "asyncio":
                            violations.append(f"{path.name}:{node.lineno}")
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.startswith("asyncio")
                ):
                    violations.append(f"{path.name}:{node.lineno}")
        assert not violations, "asyncio imported in sync core module:\n" + "\n".join(violations)


class TestNoBroadExcept:
    """Broad except clauses must be explicitly grandfathered.

    New modules should catch specific exceptions. Existing usage is
    grandfathered where justified (state machines, startup/shutdown,
    HTTP error handlers).
    """

    def test_no_broad_except(self):
        violations = []
        for path in _all_source_files():
            for i, line in enumerate(path.read_text().splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("except Exception") and "broad-except" not in line:
                    violations.append(f"{path.name}:{i}: {stripped}")
        assert not violations, (
            "Broad except clause in non-grandfathered module "
            "(use a specific exception or add # broad-except comment):\n" + "\n".join(violations)
        )


class TestNoFrameworkImportsInServices:
    """Services must not import FastAPI or Starlette.

    Services should be framework-independent for testability.
    All web framework types come via dependency injection.
    """

    _FRAMEWORK_MODULES = {"fastapi", "starlette"}

    def test_no_framework_imports(self):
        violations = []
        for path in _python_files(SERVICES):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in self._FRAMEWORK_MODULES:
                            violations.append(f"{path.name}:{node.lineno}: import {alias.name}")
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.split(".")[0] in self._FRAMEWORK_MODULES
                ):
                    violations.append(f"{path.name}:{node.lineno}: from {node.module}")
        assert not violations, (
            "Framework import in service module (services must be framework-independent):\n"
            + "\n".join(violations)
        )


class TestNoDirectServiceInstantiation:
    """Route modules get services via DI, not direct construction.

    Service instantiation belongs in dependencies.py. Route modules
    should receive services as injected parameters.
    """

    _SERVICE_PATTERN = re.compile(r"\b\w+Service\(")
    _SKIP_FILES = {"dependencies.py"}

    def test_no_service_constructors_in_routes(self):
        violations = []
        for path in _python_files(ROUTES):
            if path.name in self._SKIP_FILES:
                continue
            for i, line in enumerate(path.read_text().splitlines(), 1):
                if "direct-service" in line:
                    continue
                for match in self._SERVICE_PATTERN.finditer(line):
                    violations.append(f"{path.name}:{i}: {match.group()}")
        assert not violations, (
            "Direct service instantiation in route module "
            "(use dependency injection via dependencies.py):\n" + "\n".join(violations)
        )


class TestNoDirectFileWritesInRoutes:
    """Route modules don't call open() for writes."""

    _WRITE_MODES = {"w", "wb", "a", "ab", "x", "xb"}

    def test_no_file_writes_in_routes(self):
        violations = []
        for path in _python_files(ROUTES):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                # Check for open(..., "w") pattern
                if isinstance(node.func, ast.Name) and (node.func.id == "open"):
                    for arg in node.args[1:2]:  # mode argument
                        if isinstance(arg, ast.Constant) and arg.value in self._WRITE_MODES:
                            violations.append(f"{path.name}:{node.lineno}")
                    for kw in node.keywords:
                        if (
                            kw.arg == "mode"
                            and isinstance(kw.value, ast.Constant)
                            and kw.value.value in self._WRITE_MODES
                        ):
                            violations.append(f"{path.name}:{node.lineno}")
        assert not violations, (
            "Direct file write in route module (use a service instead):\n" + "\n".join(violations)
        )
