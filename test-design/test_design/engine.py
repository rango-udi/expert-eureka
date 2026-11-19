"""Deterministic single-fault BVA, partition and decision-rule coverage.

No application code is imported. The model is a specification supplied by the
tester, not a discovered description of the implementation. Reduction preserves
all feasible obligations in this finite candidate set; it is not a claim of
global minimum size or full application coverage.
"""
from decimal import Decimal, InvalidOperation
import json
import math
import re


def number(value):
    """Read a finite decimal without binary floating-point boundary arithmetic."""
    if isinstance(value, bool):
        raise ValueError("Boolean values are not numeric boundaries.")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("Numeric boundaries must be finite.")
    return result


def matches(value, partition):
    """Match an explicit value set or inclusive/exclusive numeric interval."""
    if "values" in partition:
        return value in partition["values"]
    try:
        value = number(value)
    except (InvalidOperation, ValueError):
        return False
    for key, comparison in (("min", lambda a, b: a >= b), ("max", lambda a, b: a <= b),
                            ("above", lambda a, b: a > b), ("below", lambda a, b: a < b)):
        if key in partition and not comparison(value, number(partition[key])):
            return False
    return True


def classify(field, value):
    """Reject gaps and overlaps for each value actually used by the design."""
    found = [part for part in field["partitions"] if matches(value, part)]
    if "min" in field:
        try:
            numeric = number(value)
            in_domain = (number(field["min"]) <= numeric <= number(field["max"]) and
                         (numeric - number(field["min"])) % number(field["step"]) == 0)
        except (InvalidOperation, ValueError):
            in_domain = False
        if not in_domain:
            found = [part for part in found if not part["valid"]]
    if len(found) != 1:
        raise ValueError("Each used value must belong to exactly one partition: " + repr(value))
    return found[0]


def validate(model):
    """Validate typed UI values, partition representatives and decision bindings."""
    if not isinstance(model, dict) or model.get("schema_version") != 1:
        raise ValueError("Use a JSON object with schema_version 1.")
    if model.get("fault_policy", "single") != "single":
        raise ValueError("This engine implements the single-fault policy only.")
    fields = model.get("fields")
    if not isinstance(fields, dict) or not fields or len(fields) > 30:
        raise ValueError("Define 1..30 fields.")
    if not isinstance(model.get("constraints", []), list):
        raise ValueError("constraints must be a list.")
    for constraint in model.get("constraints", []):
        if not isinstance(constraint, dict) or not constraint.get("when") or not set(constraint["when"]) <= set(fields) or not constraint.get("reason"):
            raise ValueError("Constraints need declared fields and an explicit exclusion reason.")
    for name, field in fields.items():
        if not isinstance(name, str) or not name or not isinstance(field, dict):
            raise ValueError("Use named field objects.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name):
            raise ValueError("Use ASCII letters, digits, underscores or hyphens for field IDs.")
        if not isinstance(field.get("nominal"), str):
            raise ValueError("UI nominal values must be strings: " + name)
        if any(key in field for key in ("min", "max", "step")):
            if not all(key in field for key in ("min", "max", "step")):
                raise ValueError("Numeric fields need min, max and step together.")
            low, high, step, nominal = [number(field[k]) for k in ("min", "max", "step", "nominal")]
            if not low <= nominal <= high or low >= high or step <= 0 or (high-low) % step or (nominal-low) % step:
                raise ValueError("Require min < max, positive step and aligned bounds/nominal.")
        parts = field.get("partitions", [])
        if not isinstance(parts, list) or not all(isinstance(p, dict) and isinstance(p.get("id"), str) for p in parts):
            raise ValueError("Partitions must be a list of objects with string IDs.")
        if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", part["id"]) for part in parts):
            raise ValueError("Use simple ASCII partition IDs.")
        if not parts or len(parts) > 100 or len({p["id"] for p in parts}) != len(parts):
            raise ValueError("Use distinct partition IDs, at most 100 per field.")
        for part in parts:
            if type(part.get("valid")) is not bool or not isinstance(part.get("representative"), str):
                raise ValueError("Each partition needs valid:boolean and representative:string.")
            if not any(key in part for key in ("values", "min", "max", "above", "below")):
                raise ValueError("A partition needs a value set or numeric interval.")
            if "values" in part and (not isinstance(part["values"], list) or
                                     not all(isinstance(v, str) for v in part["values"])):
                raise ValueError("Partition value sets must contain UI strings.")
            if classify(field, part["representative"])["id"] != part["id"]:
                raise ValueError("Representative does not match its declared partition.")
        if not classify(field, field["nominal"])["valid"]:
            raise ValueError("Every nominal field must be valid.")
    table = model.get("decision_table", {"conditions": {}, "rules": []})
    if not isinstance(table, dict):
        raise ValueError("decision_table must be an object.")
    conditions = table.get("conditions", {})
    if not isinstance(conditions, dict) or len(conditions) > 12:
        raise ValueError("Decision tables support at most 12 named Boolean conditions.")
    if any(not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key) for key in conditions):
        raise ValueError("Use simple ASCII condition IDs.")
    for condition in conditions.values():
        if not isinstance(condition, dict):
            raise ValueError("Use condition objects with field/true/false bindings.")
        if condition.get("field") not in fields or not all(isinstance(condition.get(k), str) for k in ("true", "false")):
            raise ValueError("Bind every condition to a field and true/false UI values.")
        if condition["true"] == condition["false"]:
            raise ValueError("Condition true and false values must differ.")
    if len({c["field"] for c in conditions.values()}) != len(conditions):
        raise ValueError("Use one Boolean condition per field; model derived conditions in the UI journey.")
    rules = table.get("rules", [])
    if not isinstance(rules, list) or not all(isinstance(r, dict) and isinstance(r.get("id"), str) for r in rules):
        raise ValueError("Decision rules must be a list of named objects.")
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", rule["id"]) for rule in rules):
        raise ValueError("Use simple ASCII rule IDs.")
    if len({r["id"] for r in rules}) != len(rules) or len(rules) > 1000:
        raise ValueError("Use distinct rule IDs, at most 1000 rules.")
    for rule in rules:
        if set(rule["when"]) != set(conditions) or any(type(v) is not bool and v != "*" for v in rule["when"].values()):
            raise ValueError("Each rule needs every condition with true, false or '*'.")
        if not isinstance(rule.get("expected"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", rule["expected"]):
            raise ValueError("Every rule needs a named outcome.")
    for index, left in enumerate(rules):
        for right in rules[index+1:]:
            overlap = all(left["when"][key] == "*" or right["when"][key] == "*" or
                          left["when"][key] == right["when"][key] for key in conditions)
            if overlap and left["expected"] != right["expected"] and not (left.get("infeasible_reason") or right.get("infeasible_reason")):
                raise ValueError("Overlapping decision rules have conflicting outcomes.")
    return fields, table


def design(model):
    """Build obligations, merge identical executions and greedily reduce the suite.

    Returns a JSON-serializable plan including selected cases, traceability,
    exclusions and a finite-set lower bound. At most one invalid field is
    permitted. Business decision rules may involve several valid inputs.
    """
    fields, table = validate(model)
    nominal = {name: field["nominal"] for name, field in fields.items()}
    candidates, excluded, obligations = {}, [], set()
    proposed = 0

    def matching_rules(values):
        """Resolve explicit condition values without guessing application behavior."""
        assigned = {}
        for name, condition in table.get("conditions", {}).items():
            value = values[condition["field"]]
            if value == condition["true"]:
                assigned[name] = True
            elif value == condition["false"]:
                assigned[name] = False
        return [rule for rule in table.get("rules", []) if not rule.get("infeasible_reason") and
                all(truth == "*" or (key in assigned and assigned[key] == truth)
                    for key, truth in rule["when"].items())]

    def add(values, obligation=None, expected=None):
        """Attach one coverage obligation to a feasible, model-consistent candidate."""
        nonlocal proposed
        proposed += 1
        invalid = [name for name, field in fields.items() if not classify(field, values[name])["valid"]]
        reason = "single-fault policy" if len(invalid) > 1 else None
        for constraint in model.get("constraints", []):
            if all(values.get(key) == value for key, value in constraint["when"].items()):
                reason = constraint["reason"]
        if reason:
            excluded.append({"obligation": obligation, "reason": reason})
            return
        rules = matching_rules(values)
        expected = expected or (rules[0]["expected"] if rules else
                                "rejected" if invalid else "accepted")
        # A rule may reject a valid business combination, but cannot accept an invalid partition.
        if invalid and expected == "accepted":
            raise ValueError("A decision rule accepts an input classified as invalid.")
        key = json.dumps(values, sort_keys=True)
        if key in candidates and candidates[key]["expected"] != expected:
            raise ValueError("Conflicting outcomes for the same UI inputs; refine the input model.")
        case = candidates.setdefault(key, {"inputs": values, "invalid_fields": invalid,
                                          "expected": expected, "covers": set()})
        if obligation:
            case["covers"].add(obligation)
            obligations.add(obligation)

    add(nominal, "baseline")
    for name, field in fields.items():
        if "min" in field:
            low, high, step = [number(field[k]) for k in ("min", "max", "step")]
            for label, value in zip(("below", "min", "min-plus", "max-minus", "max", "above"),
                                    (low-step, low, low+step, high-step, high, high+step)):
                add({**nominal, name: format(value, "f")}, "bva:" + name + ":" + label)
        for part in field["partitions"]:
            add({**nominal, name: part["representative"]}, "ep:" + name + ":" + part["id"])
    for rule in table.get("rules", []):
        obligation = "decision:" + rule["id"]
        if rule.get("infeasible_reason"):
            excluded.append({"obligation": obligation, "reason": rule["infeasible_reason"]})
            continue
        values = dict(nominal)
        for key, truth in rule["when"].items():
            if truth != "*":
                condition = table["conditions"][key]
                values[condition["field"]] = condition["true" if truth else "false"]
        add(values, obligation, rule["expected"])
    # EP-only bundles may vary several valid fields. They cannot claim BVA
    # obligations, whose control vectors keep every other field nominal.
    valid_choices = {name: [p["representative"] for p in field["partitions"] if p["valid"]]
                     for name, field in fields.items()}
    if len(fields) > 1:
        width = max(len(values) for values in valid_choices.values())
        for index in range(width):
            add({name: values[index % len(values)] for name, values in valid_choices.items()})
        index = 0
        for name, field in fields.items():
            for part in field["partitions"]:
                if not part["valid"]:
                    values = {key: choices[index % len(choices)] for key, choices in valid_choices.items()}
                    values[name] = part["representative"]
                    add(values)
                    index += 1
    # A boundary execution may also satisfy an EP obligation without a second browser test.
    for case in candidates.values():
        for name, field in fields.items():
            obligation = "ep:" + name + ":" + classify(field, case["inputs"][name])["id"]
            obligations.add(obligation)
            case["covers"].add(obligation)
    for case in candidates.values():
        for rule in matching_rules(case["inputs"]):
            obligation = "decision:" + rule["id"]
            if obligation in obligations and case["expected"] == rule["expected"]:
                case["covers"].add(obligation)
    if not candidates:
        raise ValueError("No candidate survives the declared constraints.")
    pending, selected = set(obligations), []
    remaining = list(candidates.values())
    while pending:
        best = max(remaining, key=lambda c: len(c["covers"] & pending))
        if not (best["covers"] & pending):
            raise ValueError("Coverage cannot be satisfied by the generated candidates.")
        selected.append(best)
        pending -= best["covers"]
        remaining.remove(best)
    # Reverse deletion makes the result irredundant while retaining deterministic ordering.
    for case in selected[:][::-1]:
        others = [other for other in selected if other is not case]
        if others and set().union(*(other["covers"] for other in others)) >= obligations:
            selected.remove(case)
    forced = set()
    indexed = list(candidates.values())
    for obligation in obligations:
        owners = [index for index, case in enumerate(indexed) if obligation in case["covers"]]
        if len(owners) == 1:
            forced.add(owners[0])
    lower_bound = max(len(forced), math.ceil(len(obligations) / max(len(c["covers"]) for c in indexed)))
    for index, case in enumerate(selected, 1):
        case["id"] = "DESIGN-" + str(index).zfill(4)
        case["covers"] = sorted(case["covers"])
    return {"schema_version": 1, "policy": "single-fault", "proposed_count": proposed,
            "candidate_count": len(candidates),
            "selected_count": len(selected), "eligible_obligations": sorted(obligations),
            "declared_obligations": sorted(obligations | {item["obligation"] for item in excluded if item["obligation"]}),
            "covered_obligations": sorted(set().union(*(set(c["covers"]) for c in selected))),
            "excluded_obligations": [item for item in excluded if item["obligation"] and item["obligation"] not in obligations],
            "excluded_candidates": excluded, "coverage_basis": "eligible finite model obligations",
            "lower_bound": lower_bound, "minimum_proven": lower_bound == len(selected), "cases": selected}
