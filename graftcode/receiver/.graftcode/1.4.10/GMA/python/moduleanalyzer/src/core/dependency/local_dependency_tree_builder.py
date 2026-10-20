import json
import os
import re

from graftcode_protocol.models.dependency_tree_model import DependencyTreeModel


def _clean_version(version: str) -> str:
    return re.sub(r"^[\^~>=< ]+", "", version.strip()).split(",")[0].strip() or "0.0.0"


def _create_node(namespace: str, name: str, version: str) -> DependencyTreeModel:
    return DependencyTreeModel(
        dependency_namespace=namespace,
        dependency_name=name,
        dependency_version=version,
    )


def _add_dependencies(
    node: DependencyTreeModel, dependencies: dict[str, str] | None, namespace: str = ""
) -> None:
    if not dependencies:
        return

    for name, version_range in dependencies.items():
        if name.startswith("graft.") or name.startswith("graftcode-"):
            continue
        node.dependency_children.append(
            _create_node(namespace, name, _clean_version(version_range))
        )


def _parse_pyproject_dependencies(path: str) -> tuple[str, str, dict[str, str]]:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore

    with open(path, "rb") as file:
        data = tomllib.load(file)

    project = data.get("project", {})
    name = project.get("name") or os.path.basename(os.path.dirname(path))
    version = project.get("version") or "1.0.0"
    dependencies = project.get("dependencies", [])

    parsed: dict[str, str] = {}
    if isinstance(dependencies, list):
        for item in dependencies:
            if not isinstance(item, str):
                continue
            parts = re.split(r"(>=|<=|==|~=|!=|<|>)", item, maxsplit=1)
            dep_name = parts[0].strip()
            dep_version = parts[-1].strip() if len(parts) > 1 else "0.0.0"
            parsed[dep_name] = dep_version

    return name, version, parsed


def build_dependency_tree_from_path(source_path: str) -> DependencyTreeModel:
    config_path = None
    current = os.path.abspath(source_path)
    if os.path.isfile(current):
        current = os.path.dirname(current)

    for _ in range(6):
        candidate = os.path.join(current, "pyproject.toml")
        if os.path.isfile(candidate):
            config_path = candidate
            break
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    if config_path is None:
        raise ValueError(f"Cannot build dependency tree: pyproject.toml not found near {source_path}")

    name, version, dependencies = _parse_pyproject_dependencies(config_path)
    root = _create_node("", name, version)
    _add_dependencies(root, dependencies)
    return root
