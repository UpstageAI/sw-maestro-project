from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.main import create_app


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "FE" / "src" / "app" / "generated" / "openapi.ts"


def ref_name(ref: str) -> str:
    return ts_name(ref.rsplit("/", 1)[-1])


def ts_name(name: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", name) if part]
    candidate = "".join(part[:1].upper() + part[1:] for part in parts) or "GeneratedType"
    return candidate if not candidate[0].isdigit() else f"Type{candidate}"


def ts_type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return ref_name(schema["$ref"])
    if "anyOf" in schema:
        parts = [ts_type(item) for item in schema["anyOf"]]
        return " | ".join(dict.fromkeys(parts)) or "unknown"
    if "enum" in schema:
        return " | ".join(json.dumps(item) for item in schema["enum"])
    if "prefixItems" in schema:
        return "[" + ", ".join(ts_type(item) for item in schema["prefixItems"]) + "]"

    schema_type = schema.get("type")
    if schema_type == "array":
        return f"Array<{ts_type(schema.get('items', {}))}>"
    if schema_type == "integer" or schema_type == "number":
        return "number"
    if schema_type == "string":
        return "string"
    if schema_type == "boolean":
        return "boolean"
    if schema_type == "null":
        return "null"
    if schema_type == "object":
        if "properties" in schema:
            return object_type(schema)
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return f"Record<string, {ts_type(additional)}>"
        return "Record<string, unknown>"
    return "unknown"


def object_type(schema: dict[str, Any]) -> str:
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    if not properties:
        return "Record<string, unknown>"
    lines = ["{"]
    for name, prop in properties.items():
        optional = "" if name in required else "?"
        lines.append(f"  {json.dumps(name)}{optional}: {ts_type(prop)};")
    lines.append("}")
    return "\n".join(lines)


def render_schema_type(name: str, schema: dict[str, Any]) -> str:
    return f"export type {ts_name(name)} = {ts_type(schema)};"


def operation_helper_name(operation_id: str) -> str:
    base = operation_id.split("_v1_", 1)[0]
    parts = base.split("_")
    return parts[0] + "".join(part.title() for part in parts[1:])


def render_path_template(path: str) -> tuple[list[str], str]:
    params = re.findall(r"{([^}]+)}", path)
    template = path
    for param in params:
        template = template.replace("{" + param + "}", "${encodeURIComponent(" + param + ")}")
    if params:
        return params, f"`{template}`"
    return params, json.dumps(path)


def render_path_helpers(paths: dict[str, Any]) -> str:
    lines = ["export const openApiPaths = {"]
    for path, methods in sorted(paths.items()):
        for method, operation in sorted(methods.items()):
            operation_id = operation.get("operationId") or f"{method}_{path}"
            name = operation_helper_name(operation_id)
            params, template = render_path_template(path)
            signature = ", ".join(f"{param}: string" for param in params)
            lines.append(f"  {name}: ({signature}) => {template},")
    lines.append("} as const;")
    return "\n".join(lines)


def render_openapi_types(openapi: dict[str, Any]) -> str:
    schemas = openapi["components"]["schemas"]
    body = [
        "/* Generated from FastAPI OpenAPI schema. Do not edit by hand. */",
        "",
        render_path_helpers(openapi["paths"]),
        "",
        *[render_schema_type(name, schema) for name, schema in sorted(schemas.items())],
        "",
    ]
    return "\n\n".join(body)


def main() -> None:
    openapi = create_app().openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_openapi_types(openapi), encoding="utf-8")


if __name__ == "__main__":
    main()
