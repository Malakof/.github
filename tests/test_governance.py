from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
from format_check import (  # noqa: E402
    deterministic_precheck,
    qualitative_review_instructions,
)
from validate_labels import validate_label_names  # noqa: E402


def load_script_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OPEN_BUMP_PRS = load_script_module("open_bump_prs", "open-bump-prs.py")
VALIDATE_COMMITS = load_script_module(
    "validate_commit_messages", "validate_commit_messages.py"
)
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

        body = OPEN_BUMP_PRS.bump_pr_body(
            "v1.4.0", [".github/workflows/enforce-conventions.yml"]
        )
        self.assertIn("## Context", body)
        self.assertIn("## Acceptance criteria", body)
        self.assertIn("## Out of scope", body)
        self.assertIn("## Validation", body)

    def test_kernel_label_provenance_is_deterministic(self) -> None:
        base = {
            "title": "fix: repair governance",
            "labels": [
                {"name": "priority:p0"},
                {"name": "type:bug"},
                {"name": "crystal:stage:implementation"},
            ],
        }
        human = deterministic_precheck(
            {**base, "author": {"login": "Malakof", "is_bot": False}},
            "pr",
            self.mapping,
        )
        bot = deterministic_precheck(
            {**base, "author": {"login": "github-actions[bot]", "is_bot": True}},
            "pr",
            self.mapping,
        )
        self.assertEqual(human["manual_kernel_labels"], ["crystal:stage:implementation"])
        self.assertEqual(bot["manual_kernel_labels"], [])

    def test_qualitative_review_is_scoped_by_artifact_kind(self) -> None:
        pr_instructions = qualitative_review_instructions("pr", "fix")
        self.assertIn("Do not require issue-template headings", pr_instructions)
        self.assertIn("Sub-issue tracking is not applicable", pr_instructions)
        self.assertIn("Acceptance-criteria checklists are allowed", pr_instructions)

        issue_instructions = qualitative_review_instructions("issue", "bug")
        self.assertIn("explicit Context, Scope, Out of scope", issue_instructions)
        self.assertIn("Sub-issue tracking is not applicable", issue_instructions)

        epic_instructions = qualitative_review_instructions("issue", "epic")
        self.assertIn("EPIC child tracking", epic_instructions)
        self.assertIn("`- [ ] #N`", epic_instructions)
        self.assertIn("prefer GitHub native sub-issues", epic_instructions)
        self.assertNotIn("Sub-issue tracking is not applicable", epic_instructions)


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


class PushRevisionRangeTests(unittest.TestCase):
    def test_new_branch_has_no_incremental_range(self) -> None:
        self.assertIsNone(
            VALIDATE_COMMITS.push_revision_range(
                before=VALIDATE_COMMITS.ZERO_SHA,
                after="a" * 40,
                ref_name="feature",
                default_branch="main",
            )
        )

    @patch.object(VALIDATE_COMMITS, "is_ancestor", return_value=True)
    @patch.object(VALIDATE_COMMITS, "commit_exists", return_value=True)
    def test_fast_forward_push_uses_incremental_range(
        self, _exists, _ancestor
    ) -> None:
        before = "b" * 40
        after = "a" * 40
        self.assertEqual(
            VALIDATE_COMMITS.push_revision_range(
                before=before,
                after=after,
                ref_name="feature",
                default_branch="main",
            ),
            f"{before}..{after}",
        )

    @patch.object(VALIDATE_COMMITS, "git", return_value="c" * 40 + "\n")
    @patch.object(VALIDATE_COMMITS, "is_ancestor", return_value=False)
    @patch.object(VALIDATE_COMMITS, "commit_exists", return_value=True)
    def test_rebased_feature_push_uses_default_branch_merge_base(
        self, _exists, _ancestor, merge_base
    ) -> None:
        after = "a" * 40
        self.assertEqual(
            VALIDATE_COMMITS.push_revision_range(
                before="b" * 40,
                after=after,
                ref_name="codex/rebased-feature",
                default_branch="main",
            ),
            f"{'c' * 40}..{after}",
        )
        merge_base.assert_called_once_with(["merge-base", after, "origin/main"])

    @patch.object(VALIDATE_COMMITS, "is_ancestor", return_value=False)
    @patch.object(VALIDATE_COMMITS, "commit_exists", return_value=True)
    def test_non_fast_forward_default_branch_fails_closed(
        self, _exists, _ancestor
    ) -> None:
        with self.assertRaisesRegex(ValueError, "default branch 'main'"):
            VALIDATE_COMMITS.push_revision_range(
                before="b" * 40,
                after="a" * 40,
                ref_name="main",
                default_branch="main",
            )

    @patch.object(VALIDATE_COMMITS, "commit_exists", return_value=False)
    def test_missing_pushed_commit_fails_closed(self, _exists) -> None:
        with self.assertRaisesRegex(ValueError, "unavailable after checkout"):
            VALIDATE_COMMITS.push_revision_range(
                before="b" * 40,
                after="a" * 40,
                ref_name="feature",
                default_branch="main",
            )


if __name__ == "__main__":
    unittest.main()
