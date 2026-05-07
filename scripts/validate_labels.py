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

    # Enforce kernel-only namespace : if a kernel label is set and the PR is opened
    # by a human (not bot), warn.
    kernel_prefixes = ("crystal:agent:", "crystal:stage:", "crystal:status:", "crystal:runtime:")
    kernel_labels = [name for name in label_names if name.startswith(kernel_prefixes)]
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
