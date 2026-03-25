from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "contracts"
EXAMPLES_DIR = CONTRACTS_DIR / "examples"

TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
}


def is_valid_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_value(schema: dict[str, Any], value: Any, path: str) -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")

    if expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return [f"{path}: expected integer"]
    elif expected_type and not isinstance(value, TYPE_MAP[expected_type]):
        return [f"{path}: expected {expected_type}"]

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']}")

    if expected_type == "string":
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{path}: minLength {min_length}")
        if schema.get("format") == "date-time" and not is_valid_datetime(value):
            errors.append(f"{path}: invalid date-time")

    if expected_type in {"integer", "number"}:
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and value < minimum:
            errors.append(f"{path}: minimum {minimum}")
        if maximum is not None and value > maximum:
            errors.append(f"{path}: maximum {maximum}")

    if expected_type == "object":
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key}: missing required property")
        if schema.get("additionalProperties") is False:
            extra_keys = sorted(set(value.keys()) - set(properties.keys()))
            for key in extra_keys:
                errors.append(f"{path}.{key}: additional property not allowed")
        for key, subschema in properties.items():
            if key in value:
                errors.extend(validate_value(subschema, value[key], f"{path}.{key}"))

    if expected_type == "array":
        item_schema = schema.get("items", {})
        for index, item in enumerate(value):
            errors.extend(validate_value(item_schema, item, f"{path}[{index}]"))

    return errors


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_file(schema_path: Path, example_path: Path) -> list[str]:
    schema = load_json(schema_path)
    payload = load_json(example_path)
    return validate_value(schema, payload, example_path.name)


def validate_jsonl(schema_path: Path, example_path: Path) -> list[str]:
    schema = load_json(schema_path)
    errors: list[str] = []
    for index, line in enumerate(example_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        payload = json.loads(line)
        errors.extend(validate_value(schema, payload, f"{example_path.name}[{index}]"))
    return errors


def main() -> int:
    pairs = [
        ("raw-log.schema.json", "raw-log.sample.json"),
        ("analyze-request.schema.json", "analyze-request.sample.json"),
        ("analyze-response.schema.json", "analyze-response.sample.json"),
        ("processed-log.schema.json", "processed-log.sample.json"),
    ]

    errors: list[str] = []

    for schema_name, example_name in pairs:
        errors.extend(
            validate_file(CONTRACTS_DIR / schema_name, EXAMPLES_DIR / example_name)
        )

    errors.extend(
        validate_jsonl(
            CONTRACTS_DIR / "raw-log.schema.json",
            EXAMPLES_DIR / "raw-logs.sample.jsonl",
        )
    )

    if errors:
        for error in errors:
            print(error)
        return 1

    print("Contracts and examples are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
