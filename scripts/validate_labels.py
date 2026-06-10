#!/usr/bin/env python3
"""Validate that a PR carries the required labels per labels.yaml.

Required dimensions : exactly one priority:p* and one type:*.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml


def gh_json(args: list[str]) -> object:
    result = subprocess.run(["gh"] + args, capture_output=True, text=True, check=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--labels-file", type=Path, required=True)
    parser.add_argument("--blocking", default="true")
    args = parser.parse_args()

    blocking = args.blocking.lower() == "true"
    severity = "error" if blocking else "warning"

    payload = gh_json([
        "pr", "view", str(args.pr),
        "--repo", args.repo,
        "--json", "labels",
    ]) or {}
    label_names = {label["name"] for label in payload.get("labels", [])}  # type: ignore[index]

    issues: list[str] = []

    priority_labels = [name for name in label_names if name.startswith("priority:p")]
    if len(priority_labels) != 1:
        issues.append(
            f"Expected exactly one priority:p* label, got {sorted(priority_labels) or 'none'}."
        )

    type_labels = [name for name in label_names if name.startswith("type:")]
    if len(type_labels) != 1:
        issues.append(
            f"Expected exactly one type:* label, got {sorted(type_labels) or 'none'}."
        )

    type_from_title = None
    pr_payload = gh_json([
        "pr", "view", str(args.pr),
        "--repo", args.repo,
        "--json", "title",
    ]) or {}
    title = pr_payload.get("title", "") if isinstance(pr_payload, dict) else ""
    if ":" in title:
        type_from_title = title.split(":", 1)[0].split("(", 1)[0].rstrip("!")
    type_map = {"feat": "feature"}
    if type_from_title:
        expected_type = f"type:{type_map.get(type_from_title, type_from_title)}"
        if len(type_labels) == 1 and type_labels[0] != expected_type:
            issues.append(f"Expected type label {expected_type!r} to match PR title, got {type_labels[0]!r}.")

    # Enforce kernel-only namespace: if a kernel label is set, warn. The workflow
    # cannot reliably distinguish kernel projection from human application.
    kernel_prefixes = ("crystal:agent:", "crystal:stage:", "crystal:status:", "crystal:runtime:")
    kernel_exact = {"crystal:mission", "crystal:parent", "crystal:child"}
    kernel_labels = [
        name for name in label_names if name.startswith(kernel_prefixes) or name in kernel_exact
    ]
    if kernel_labels:
        print(f"::notice::Kernel-projected labels detected: {sorted(kernel_labels)}. These should only be set by paperclip kernel.")

    if issues:
        for msg in issues:
            print(f"::{severity}::{msg}")
        return 1 if blocking else 0

    print(f"::notice::Labels OK — priority={priority_labels[0]} type={type_labels[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
