"""Utility functions."""

import json
from typing import Any


def normalize_id(value: str) -> str:
    """Normalize a cluster or attribute ID to decimal string format.

    Converts hex strings like '0x0090' to decimal '144'.
    Keeps decimal strings as-is.
    """
    value = str(value).strip()
    if value.startswith("0x") or value.startswith("0X"):
        try:
            return str(int(value, 16))
        except ValueError:
            return value
    return value


def safe_json(value: Any) -> str:
    """Convert a value to a JSON string safely."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def parse_path_fields(path_value: Any) -> tuple[str, str, str, str]:
    """Parse path fields from various formats.

    Returns (endpoint_id, cluster_id, attribute_id, path_text).
    """
    endpoint_id = ""
    cluster_id = ""
    attribute_id = ""

    if isinstance(path_value, dict):
        endpoint_id = str(path_value.get("endpoint") or path_value.get("endpoint_id") or "")
        cluster_id = str(path_value.get("cluster") or path_value.get("cluster_id") or "")
        attribute_id = str(
            path_value.get("attribute") or path_value.get("attribute_id") or ""
        )
        return endpoint_id, cluster_id, attribute_id, safe_json(path_value)

    if isinstance(path_value, str):
        normalized = path_value.replace(".", "/").replace("\\", "/").strip("/")
        parts = [part for part in normalized.split("/") if part]
        if len(parts) >= 3:
            endpoint_id, cluster_id, attribute_id = parts[-3], parts[-2], parts[-1]
        return endpoint_id, cluster_id, attribute_id, path_value

    if path_value is None:
        return endpoint_id, cluster_id, attribute_id, ""

    return endpoint_id, cluster_id, attribute_id, str(path_value)
