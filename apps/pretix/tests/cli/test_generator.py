"""Verify project behavior with isolated inputs and no real Docker mutations."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("generator", ROOT / "scripts/generate_cases.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class DataTechniqueTests(unittest.TestCase):
    def test_non_object_model_explains_the_required_json_structure(self):
        """Reject a JSON array with a clear model-structure error before exporting rows."""
        with self.assertRaisesRegex(ValueError, "JSON object with fields"):
            list(generator.generate([]))
    def test_boolean_bounds_are_rejected_before_generation(self):
        """Reject booleans used as integer bounds; raise no error for unrelated tests."""
        self.model["fields"]["quantity"]["min"] = True
        with self.assertRaisesRegex(ValueError, "integer min <= nominal <= max"):
            list(generator.generate(self.model))

    def test_incomplete_decision_rule_explains_the_missing_condition(self):
        """Reject a rule with missing condition values and identify its rule number."""
        self.model["decision_table"]["rules"][0]["when"] = [True]
        with self.assertRaisesRegex(ValueError, "Decision rule 1"):
            list(generator.generate(self.model))

    def test_every_exported_row_explains_its_technique(self):
        """Require each generated record to include a readable purpose for review."""
        self.assertTrue(all(len(row["purpose"]) > 30 for row in self.rows))
    def setUp(self):
        """Create an isolated project copy and test fixtures; return None without changing real Docker resources."""
        self.model = json.loads((ROOT / "tests/data/INPUT_MODEL.json").read_text())
        self.rows = [row for row in generator.generate(self.model) if row]

    def test_robust_bva_has_both_outside_values(self):
        """Verify robust bva has both outside values. Return None or raise AssertionError on a regression."""
        rows = [row for row in self.rows if row["technique"] == "robust_bva"]
        values = {json.loads(row["inputs"])["quantity"] for row in rows}
        self.assertEqual(values, {0, 1, 2, 9, 10, 11})
        self.assertEqual(sum(row["fail_mode"] == "single_fail" for row in rows), 2)

    def test_weak_robust_never_includes_multiple_invalid_fields(self):
        """Verify weak robust never includes multiple invalid fields. Return None or raise AssertionError on a regression."""
        rows = [row for row in self.rows if row["technique"] == "weak_robust_ep"]
        self.assertTrue(rows)
        self.assertTrue(all(row["fail_mode"] != "multi_fail" for row in rows))

    def test_multiple_failures_are_separate_cases(self):
        """Verify multiple failures are separate cases. Return None or raise AssertionError on a regression."""
        rows = [row for row in self.rows if row["technique"] == "multi_fail"]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["invalid_fields"] == "quantity,voucher" for row in rows))

    def test_decision_table_has_four_rules(self):
        """Verify decision table has four rules. Return None or raise AssertionError on a regression."""
        rows = [row for row in self.rows if row["technique"] == "decision_table"]
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({row["expected"] for row in rows}), 4)
