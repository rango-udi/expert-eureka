"""Check mathematical coverage invariants inside the tools image, without browser I/O."""
import copy
import unittest
from test_design.engine import design


def model():
    """Build a small independent specification with an explicit missing-value class."""
    return {"schema_version": 1, "fields": {"amount": {
        "nominal": "5", "min": "0", "max": "10", "step": "1", "partitions": [
            {"id": "valid", "valid": True, "representative": "5", "min": "0", "max": "10"},
            {"id": "low", "valid": False, "representative": "-1", "below": "0"},
            {"id": "high", "valid": False, "representative": "11", "above": "10"},
            {"id": "missing", "valid": False, "representative": "", "values": [""]}]}},
        "decision_table": {"conditions": {"allowed": {"field": "amount", "true": "5", "false": "-1"}},
            "rules": [{"id": "accept", "when": {"allowed": True}, "expected": "accepted"},
                      {"id": "reject", "when": {"allowed": False}, "expected": "rejected"}]}}


class DesignTests(unittest.TestCase):
    """Test coverage and fault counts rather than mirroring implementation branches."""

    def test_union_covers_every_eligible_obligation_without_duplicate_executions(self):
        """BVA and EP share executions; every retained obligation still has a witness."""
        plan = design(model())
        self.assertEqual(plan["selected_count"], 8)
        self.assertEqual(plan["eligible_obligations"], plan["covered_obligations"])
        self.assertEqual(len({tuple(c["inputs"].items()) for c in plan["cases"]}), 8)
        self.assertTrue(plan["minimum_proven"])

    def test_selected_suite_is_irredundant(self):
        """Removing any selected execution must lose at least one model obligation."""
        plan = design(model())
        for index in range(len(plan["cases"])):
            covered = set().union(*(set(c["covers"]) for i, c in enumerate(plan["cases"]) if i != index))
            self.assertNotEqual(covered, set(plan["eligible_obligations"]))

    def test_decimal_neighbors_are_exact(self):
        """Decimal increments must never create binary-float boundary artifacts."""
        value = model()
        field = value["fields"]["amount"]
        field.update(min="0.00", max="10.00", nominal="5.00", step="0.01")
        field["partitions"][0]["representative"] = "5.00"
        field["partitions"][1]["representative"] = "-0.01"
        field["partitions"][2]["representative"] = "10.01"
        value.pop("decision_table")
        inputs = {c["inputs"]["amount"] for c in design(value)["cases"]}
        self.assertTrue({"-0.01", "0.00", "0.01", "9.99", "10.00", "10.01"} <= inputs)

    def test_multiple_invalid_inputs_are_reported_as_excluded(self):
        """Single-fault coverage must not silently include a two-fault decision row."""
        value = model()
        value["fields"]["method"] = {"nominal": "card", "partitions": [
            {"id": "known", "valid": True, "representative": "card", "values": ["card"]},
            {"id": "unknown", "valid": False, "representative": "unknown", "values": ["unknown"]}]}
        value["decision_table"] = {"conditions": {
            "allowed": {"field": "amount", "true": "5", "false": "-1"},
            "known": {"field": "method", "true": "card", "false": "unknown"}}, "rules": [
                {"id": "both", "when": {"allowed": False, "known": False}, "expected": "rejected"}]}
        plan = design(value)
        self.assertTrue(all(len(c["invalid_fields"]) <= 1 for c in plan["cases"]))
        self.assertIn({"obligation": "decision:both", "reason": "single-fault policy"}, plan["excluded_obligations"])

    def test_conflicting_wildcard_rules_fail_before_export(self):
        """An ambiguous decision oracle must never be resolved by rule ordering."""
        value = model()
        value["decision_table"]["rules"][0]["when"]["allowed"] = "*"
        with self.assertRaisesRegex(ValueError, "conflicting"):
            design(value)

    def test_overlapping_used_partitions_are_rejected(self):
        """The same representative cannot be both valid and invalid."""
        value = model()
        extra = copy.deepcopy(value["fields"]["amount"]["partitions"][0])
        extra.update(id="overlap", valid=False)
        value["fields"]["amount"]["partitions"].append(extra)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            design(value)

    def test_valid_ep_classes_can_share_one_execution(self):
        """Combine valid enum partitions to avoid an unnecessary one-field-only suite."""
        value = {"schema_version": 1, "fields": {}}
        for field, values in (("scent", ["rose", "wood", "citrus"]), ("size", ["small", "large"])):
            value["fields"][field] = {"nominal": values[0], "partitions": [
                {"id": item, "valid": True, "representative": item, "values": [item]} for item in values]}
        plan = design(value)
        self.assertEqual(plan["selected_count"], 3)
        self.assertEqual(plan["eligible_obligations"], plan["covered_obligations"])

    def test_off_step_partition_remains_a_single_invalid_input(self):
        """A numeric interval must not incorrectly classify a fractional-step error as valid."""
        value = model()
        value["fields"]["amount"]["partitions"].append({"id": "off-step", "valid": False,
            "representative": "5.5", "values": ["5.5"]})
        case = next(c for c in design(value)["cases"] if c["inputs"]["amount"] == "5.5")
        self.assertEqual(case["invalid_fields"], ["amount"])
        self.assertEqual(case["expected"], "rejected")
