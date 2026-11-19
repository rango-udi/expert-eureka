"""Export a traceable test plan and a DataDriver suite inside a tools container."""
import argparse
import base64
import csv
import json
from pathlib import Path
from test_design.engine import design
from test_design.specification import load_specification, semantic_hash


def export(model_path, output):
    """Write a frozen model, plan, semicolon CSV and executable Robot template."""
    model = load_specification(model_path)
    plan = design(model)
    if "attribution" in model:
        plan["attribution"] = model["attribution"]
    plan["model_sha256"] = semantic_hash(model)
    plan["execution_status"] = "not_executed"
    ui = model.get("ui", {})
    if set(ui.get("bindings", {})) != set(model["fields"]):
        raise ValueError("Bind every model field to a UI control.")
    if not {case["expected"] for case in plan["cases"]} <= set(ui.get("oracles", {})):
        raise ValueError("Define a UI oracle for every generated outcome.")
    if not all(key in ui for key in ("path", "submit")):
        raise ValueError("Provide the UI path and submit control.")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "model.json").write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    (output / "coverage.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    with (output / "cases.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(["*** Test Cases ***", "${payload}", "${outcome}", "[Tags]", "[Documentation]"])
        for case in plan["cases"]:
            writer.writerow([case["id"], base64.b64encode(json.dumps(case["inputs"]).encode("utf-8")).decode("ascii"), case["expected"],
                             "generated-design,single-fault", ", ".join(case["covers"])])
    suite = """*** Settings ***
Library    Browser
Library    DataDriver    file=${CURDIR}/cases.csv    dialect=userdefined    delimiter=;    encoding=utf-8
Library    test_design.journey.RobotJourney    ${CURDIR}/model.json
Test Template    Execute Modelled Journey
Test Tags    generated-design    single-fault

*** Test Cases ***
Generated case placeholder
    {}    accepted

*** Keywords ***
Execute Modelled Journey
    [Arguments]    ${payload}    ${outcome}
    Run Modelled Journey    ${payload}    ${outcome}
"""
    (output / "run.robot").write_text(suite, encoding="utf-8")
    return plan


def main():
    """Parse model/output locations and print the scope of the generated coverage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    try:
        plan = export(options.model, options.output)
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as error:
        parser.exit(2, "Invalid design model: " + str(error) + "\n")
    print("Selected", plan["selected_count"], "cases from", plan["candidate_count"], "candidates.")
    print("Eligible obligations:", len(plan["covered_obligations"]), "/", len(plan["eligible_obligations"]))
    print("Excluded obligations:", len(plan["excluded_obligations"]), "; see coverage.json.")


if __name__ == "__main__":
    main()
