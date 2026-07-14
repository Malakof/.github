"""Shared Crystal title grammar and title-to-label governance policy."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ALLOWED_CONVENTIONAL_TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)
ISSUE_TITLE_TYPES = ("feature", "bug", "chore", "docs", "refactor", "spike", "test")
ALL_GOVERNED_TITLE_TYPES = frozenset((*ALLOWED_CONVENTIONAL_TYPES, *ISSUE_TITLE_TYPES, "epic"))

_CONVENTIONAL_TYPE_PATTERN = "|".join(ALLOWED_CONVENTIONAL_TYPES)
CONVENTIONAL_PREFIX_PATTERN = (
    rf"(?P<type>{_CONVENTIONAL_TYPE_PATTERN})"
    r"(?:\((?P<scope>[a-z0-9._-]+)\))?"
    r"(?P<bang>!)?"
)
CONVENTIONAL_TITLE_RE = re.compile(rf"^{CONVENTIONAL_PREFIX_PATTERN}: (?P<subject>.+)$")
CONVENTIONAL_COMMIT_RE = re.compile(
    rf"^{CONVENTIONAL_PREFIX_PATTERN}: (?P<emoji>\S+) (?P<subject>.+)$"
)
ISSUE_TITLE_RE = re.compile(
    rf"^(?P<type>{'|'.join(ISSUE_TITLE_TYPES)}): (?P<subject>.+)$"
)
EPIC_TITLE_RE = re.compile(r"^\[EPIC\] (?P<subject>.+)$")


def load_title_type_map(labels_file: Path) -> dict[str, str]:
    """Load and validate the total governed title-type mapping."""
    data = yaml.safe_load(labels_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{labels_file}: expected a YAML object")

    raw_mapping = data.get("title_type_map")
    if not isinstance(raw_mapping, dict):
        raise ValueError(f"{labels_file}: title_type_map must be an object")
    mapping = {str(key): str(value) for key, value in raw_mapping.items()}

    keys = set(mapping)
    missing = sorted(ALL_GOVERNED_TITLE_TYPES - keys)
    unexpected = sorted(keys - ALL_GOVERNED_TITLE_TYPES)
    if missing or unexpected:
        raise ValueError(
            f"{labels_file}: title_type_map domain mismatch; missing={missing}, unexpected={unexpected}"
        )

    categories = data.get("categories")
    type_category = categories.get("type") if isinstance(categories, dict) else None
    raw_labels = type_category.get("labels") if isinstance(type_category, dict) else None
    canonical_labels = {
        item.get("name")
        for item in raw_labels or []
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    invalid_values = sorted(set(mapping.values()) - canonical_labels)
    if invalid_values:
        raise ValueError(
            f"{labels_file}: title_type_map references non-canonical labels {invalid_values}"
        )
    return mapping
