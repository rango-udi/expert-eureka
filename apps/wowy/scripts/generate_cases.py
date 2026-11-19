"""Generate reviewable test data without executing application business flows."""

import csv
import itertools
import json
from pathlib import Path
import sys
from collections import Counter

CASE_FIELDS = [
    "technique",
    "inputs",
    "invalid_fields",
    "fail_mode",
    "expected",
    "purpose",
]
PURPOSES = {
    "robust_bva": "Change one integer field at its boundaries; keep other fields nominal.",
    "weak_robust_ep": "Change one field to a declared partition representative; keep other fields nominal.",
    "multi_fail": "Combine invalid representatives in at least two fields.",
    "decision_table": "Apply one explicitly supplied condition combination and its expected decision.",
}


def validate_model(model: dict) -> dict:
    """Check the generation model before exporting any rows.

    Args:
        model: Parsed JSON with fields and a decision_table.
    Returns:
        The nonempty fields mapping after validation.
    Raises:
        ValueError: Bounds, representatives, or decision rules are inconsistent.
    """
    if not isinstance(model, dict):
        raise ValueError(
            "The input model must be a JSON object with fields and decision_table entries."
        )
    fields = model.get("fields")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("The model must define at least one field under fields.")
    for name, field in fields.items():
        if not isinstance(field, dict):
            raise ValueError(
                f"Field {name} must be an object containing nominal values and representative lists."
            )
        for key in ("nominal", "valid_representatives", "invalid_representatives"):
            if key not in field:
                raise ValueError(
                    f"Field {name} is missing {key}. Add it to INPUT_MODEL.json."
                )
        for key in ("valid_representatives", "invalid_representatives"):
            if not isinstance(field[key], list):
                raise ValueError(f"Field {name}: {key} must be a JSON list.")
        if "min" in field or "max" in field:
            values = [field.get(key) for key in ("min", "max", "nominal")]
            if (
                not all(type(value) is int for value in values)
                or not values[0] <= values[2] <= values[1]
            ):
                raise ValueError(
                    f"Field {name} needs integer min <= nominal <= max for boundary generation."
                )
    table = model.get("decision_table", {})
    if not isinstance(table, dict):
        raise ValueError(
            "decision_table must be an object containing conditions and rules."
        )
    conditions = table.get("conditions", [])
    if (
        not isinstance(conditions, list)
        or not conditions
        or not all(isinstance(name, str) and name for name in conditions)
        or len(set(conditions)) != len(conditions)
    ):
        raise ValueError(
            "decision_table.conditions must contain distinct condition names."
        )
    rules = table.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError(
            "decision_table.rules must contain at least one rule with when and expected entries."
        )
    for index, rule in enumerate(rules, start=1):
        if (
            not isinstance(rule, dict)
            or not isinstance(rule.get("when"), list)
            or len(rule["when"]) != len(conditions)
            or not isinstance(rule.get("expected"), str)
            or not rule["expected"]
        ):
            raise ValueError(
                f"Decision rule {index} needs one when value per condition and an expected result."
            )
    return fields


def boundary_variants(fields: dict, nominal: dict):
    """Yield boundary inputs from field definitions and a nominal input mapping.

    Yields:
        Input mappings, invalid field names, and model-based expected outcomes.
        Only one numeric field changes per case; duplicate values are allowed here.
    """
    yield nominal, [], "valid_by_model"
    for name, field in fields.items():
        if "min" not in field:
            continue
        low, high = field["min"], field["max"]
        for value in (low - 1, low, low + 1, high - 1, high, high + 1):
            invalid = [name] if value < low or value > high else []
            yield {**nominal, name: value}, invalid, (
                "reject_by_model" if invalid else "valid_by_model"
            )


def partition_variants(fields: dict, nominal: dict):
    """Yield one-field partition substitutions using declared representative lists.

    Args:
        fields: Validated model fields with valid and invalid representatives.
        nominal: Baseline input mapping for all unchanged fields.
    Yields:
        Inputs, invalid field names, and expected model outcomes; never multi-fail cases.
    """
    yield nominal, [], "valid_by_model"
    for name, field in fields.items():
        for valid, representatives in (
            (True, field["valid_representatives"]),
            (False, field["invalid_representatives"]),
        ):
            for value in representatives:
                yield {**nominal, name: value}, [] if valid else [name], (
                    "valid_by_model" if valid else "reject_by_model"
                )


def multiple_invalid_variants(fields: dict):
    """Yield combinations with invalid values in at least two declared fields.

    Args:
        fields: Validated field definitions including nominal and invalid values.
    Yields:
        Input mappings, invalid field names, and reject_by_model outcomes.
        This Cartesian expansion is separate from weak robust partition coverage.
    """
    names = list(fields)
    choices = [
        [(field["nominal"], False)]
        + [(value, True) for value in field["invalid_representatives"]]
        for field in fields.values()
    ]
    for combination in itertools.product(*choices):
        invalid = [name for name, (_, bad) in zip(names, combination) if bad]
        if len(invalid) >= 2:
            values = {name: value for name, (value, _) in zip(names, combination)}
            yield values, invalid, "reject_by_model"


def generate(model: dict):
    """Combine generation techniques and yield unique, explained CSV-ready records.

    Args:
        model: Parsed input model containing fields and explicit decision rules.
    Yields:
        Dictionaries matching CASE_FIELDS. Deduplication is per technique and input.
        Expected outcomes describe the supplied model, not observed Wowy behavior.
    """
    fields = validate_model(model)
    nominal = {name: field["nominal"] for name, field in fields.items()}
    table = model["decision_table"]
    decisions = (
        (dict(zip(table["conditions"], rule["when"])), [], rule["expected"])
        for rule in table["rules"]
    )
    groups = (
        ("robust_bva", boundary_variants(fields, nominal)),
        ("weak_robust_ep", partition_variants(fields, nominal)),
        ("multi_fail", multiple_invalid_variants(fields)),
        ("decision_table", decisions),
    )
    seen = set()
    for technique, variants in groups:
        for values, invalid, expected in variants:
            key = technique, json.dumps(values, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            fail_mode = (
                "valid"
                if not invalid
                else "single_fail" if len(invalid) == 1 else "multi_fail"
            )
            yield {
                "technique": technique,
                "inputs": json.dumps(values, ensure_ascii=False),
                "invalid_fields": ",".join(invalid),
                "fail_mode": fail_mode,
                "expected": expected,
                "purpose": PURPOSES[technique],
            }


def main() -> int:
    """Export the fixed project input model to CSV and a machine-readable summary.

    Returns:
        Zero after writing reports/generated_cases.csv and case_generation_summary.json;
        two if the model or output cannot be processed. Prints next steps in English.
    """
    root = Path(__file__).resolve().parents[1]
    output = root / "reports/generated_cases.csv"
    try:
        model = json.loads(
            (root / "tests/data/INPUT_MODEL.json").read_text(encoding="utf-8")
        )
        rows = list(generate(model))
        output.parent.mkdir(exist_ok=True)
        with output.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=CASE_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        summary = {
            "status": "generated_not_executed",
            "case_count": len(rows),
            "technique_counts": dict(Counter(row["technique"] for row in rows)),
            "technique_descriptions": PURPOSES,
            "meaning": "Expected results come from the input model. No browser or Wowy behavior was checked.",
            "next_step": "Review each case and connect it to a Robot UI keyword and a business assertion.",
        }
        (output.parent / "case_generation_summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: Test data could not be generated. {error}", file=sys.stderr)
        print(
            "Review tests/data/INPUT_MODEL.json and verify that reports/ is writable, then run cmdc generate again.",
            file=sys.stderr,
        )
        return 2
    print(f"Generated {len(rows)} test-data cases: {output}")
    print(
        "These cases were not executed. Read reports/case_generation_summary.json for coverage and next steps."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
