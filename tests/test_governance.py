from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from conventions import (  # noqa: E402
    ALL_GOVERNED_TITLE_TYPES,
    CONVENTIONAL_COMMIT_RE,
    CONVENTIONAL_TITLE_RE,
    load_title_type_map,
)
from format_check import deterministic_precheck  # noqa: E402
from validate_labels import validate_label_names  # noqa: E402


def load_script_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OPEN_BUMP_PRS = load_script_module("open_bump_prs", "open-bump-prs.py")
LABELS_FILE = REPO_ROOT / "governance" / "labels.yaml"

EXPECTED_PR_MAPPING = {
    "feat": "type:feature",
    "fix": "type:bug",
    "docs": "type:docs",
    "style": "type:chore",
    "refactor": "type:refactor",
    "perf": "type:refactor",
    "test": "type:test",
    "build": "type:chore",
    "ci": "type:chore",
    "chore": "type:chore",
    "revert": "type:bug",
}
EXPECTED_ISSUE_MAPPING = {
    "feature": "type:feature",
    "bug": "type:bug",
    "chore": "type:chore",
    "docs": "type:docs",
    "refactor": "type:refactor",
    "spike": "type:spike",
    "test": "type:test",
    "epic": "type:epic",
}


class GovernanceTypeMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mapping = load_title_type_map(LABELS_FILE)

    def test_mapping_is_total_and_uses_only_canonical_labels(self) -> None:
        expected = {**EXPECTED_PR_MAPPING, **EXPECTED_ISSUE_MAPPING}
        self.assertEqual(self.mapping, expected)
        self.assertEqual(set(self.mapping), set(ALL_GOVERNED_TITLE_TYPES))

        data = yaml.safe_load(LABELS_FILE.read_text(encoding="utf-8"))
        canonical = {
            item["name"] for item in data["categories"]["type"]["labels"]
        }
        self.assertLessEqual(set(self.mapping.values()), canonical)

    def test_every_conventional_pr_type_passes_both_consumers(self) -> None:
        for title_type, expected_label in EXPECTED_PR_MAPPING.items():
            with self.subTest(title_type=title_type):
                title = f"{title_type}: improve governed behavior"
                labels = {"priority:p1", expected_label}
                issues, _, _ = validate_label_names(labels, title, self.mapping)
                self.assertEqual(issues, [])

                artifact = {
                    "title": title,
                    "labels": [{"name": label} for label in sorted(labels)],
                }
                precheck = deterministic_precheck(artifact, "pr", self.mapping)
                self.assertTrue(precheck["title_format_valid"])
                self.assertEqual(precheck["expected_type_label"], expected_label)
                self.assertTrue(precheck["type_label_matches_title"])

    def test_wrong_pr_label_fails_with_the_canonical_expectation(self) -> None:
        issues, _, _ = validate_label_names(
            {"priority:p0", "type:chore"},
            "fix: repair the validator",
            self.mapping,
        )
        self.assertEqual(len(issues), 1)
        self.assertIn("'type:bug'", issues[0])

    def test_issue_title_types_keep_their_functional_labels(self) -> None:
        for title_type, expected_label in EXPECTED_ISSUE_MAPPING.items():
            with self.subTest(title_type=title_type):
                title = "[EPIC] Coordinate delivery" if title_type == "epic" else (
                    f"{title_type}: coordinate delivery"
                )
                artifact = {
                    "title": title,
                    "labels": [
                        {"name": "priority:p1"},
                        {"name": expected_label},
                    ],
                }
                precheck = deterministic_precheck(artifact, "issue", self.mapping)
                self.assertTrue(precheck["title_format_valid"])
                self.assertEqual(precheck["expected_type_label"], expected_label)
                self.assertTrue(precheck["type_label_matches_title"])

    def test_title_grammars_are_artifact_specific(self) -> None:
        issue_artifact = {
            "title": "fix: invalid issue title",
            "labels": [{"name": "priority:p1"}, {"name": "type:bug"}],
        }
        pr_artifact = {
            "title": "bug: invalid PR title",
            "labels": [{"name": "priority:p1"}, {"name": "type:bug"}],
        }
        self.assertFalse(
            deterministic_precheck(issue_artifact, "issue", self.mapping)["title_format_valid"]
        )
        self.assertFalse(
            deterministic_precheck(pr_artifact, "pr", self.mapping)["title_format_valid"]
        )

    def test_breaking_change_bang_follows_conventional_commits(self) -> None:
        self.assertIsNotNone(CONVENTIONAL_TITLE_RE.match("feat(api)!: change contract"))
        self.assertIsNone(CONVENTIONAL_TITLE_RE.match("feat!(api): change contract"))
        self.assertIsNotNone(
            CONVENTIONAL_COMMIT_RE.match("feat(api)!: ✨ change contract")
        )

    def test_mapping_loader_fails_closed_on_partial_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            labels_file = Path(tmp) / "labels.yaml"
            labels_file.write_text(
                yaml.safe_dump(
                    {
                        "title_type_map": {"feat": "type:feature"},
                        "categories": {
                            "type": {"labels": [{"name": "type:feature"}]}
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "domain mismatch"):
                load_title_type_map(labels_file)

    def test_generated_bump_pr_contract_passes_old_and_new_taxonomy(self) -> None:
        title = OPEN_BUMP_PRS.bump_pr_title("v1.4.0")
        issues, _, _ = validate_label_names(
            set(OPEN_BUMP_PRS.PR_LABELS), title, self.mapping
        )
        self.assertEqual(issues, [])


class WorkflowRuntimeTests(unittest.TestCase):
    def test_workflows_use_node_24_action_majors(self) -> None:
        workflow_root = REPO_ROOT / ".github" / "workflows"
        contents = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted(workflow_root.glob("*.yml"))
        }
        self.assertTrue(contents)
        for name, content in contents.items():
            with self.subTest(workflow=name):
                self.assertNotIn("actions/checkout@v4", content)
                self.assertNotIn("actions/setup-python@v5", content)
        self.assertIn("actions/checkout@v5", contents["test.yml"])
        self.assertIn("actions/setup-python@v6", contents["test.yml"])


if __name__ == "__main__":
    unittest.main()
