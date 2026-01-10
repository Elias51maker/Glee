from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


@dataclass(frozen=True)
class LintResult:
    tools_dir: Path
    tool_files: list[Path]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def load_tool_schema() -> dict:
    schema_path = resources.files("glee.schemas").joinpath("tool.schema.json")
    with schema_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_tool_files(root: Path) -> list[Path]:
    tools_dir = root / ".glee" / "tools"
    if not tools_dir.is_dir():
        return []
    tool_files: list[Path] = []
    for entry in sorted(tools_dir.iterdir()):
        if not entry.is_dir():
            continue
        tool_file = entry / "tool.yml"
        if tool_file.is_file():
            tool_files.append(tool_file)
    return tool_files


def _format_error_path(path_parts) -> str:
    if not path_parts:
        return "<root>"
    return ".".join(str(part) for part in path_parts)


def validate_tool_file(tool_file: Path, validator: Draft202012Validator) -> list[str]:
    try:
        content = yaml.safe_load(tool_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"{tool_file}: YAML parse error: {exc}"]

    if not isinstance(content, dict):
        return [f"{tool_file}: Expected mapping at root"]

    errors = sorted(validator.iter_errors(content), key=lambda e: list(e.path))
    messages = []
    for error in errors:
        path = _format_error_path(error.path)
        messages.append(f"{tool_file}: {path}: {error.message}")
    return messages


def lint_tools(root: Path) -> LintResult:
    root = root.resolve()
    tools_dir = root / ".glee" / "tools"
    tool_files = find_tool_files(root)
    if not tool_files:
        return LintResult(tools_dir=tools_dir, tool_files=[], errors=[])

    schema = load_tool_schema()
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for tool_file in tool_files:
        errors.extend(validate_tool_file(tool_file, validator))

    return LintResult(tools_dir=tools_dir, tool_files=tool_files, errors=errors)
