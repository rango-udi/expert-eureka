"""Execute generated cases through Browser using an allowlisted UI action model."""
import json
import base64
import os
from pathlib import Path
from urllib.parse import urlsplit
from robot.libraries.BuiltIn import BuiltIn


class RobotJourney:
    """Bind data to an existing browser journey without importing application code."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    def __init__(self, model_path):
        """Read a frozen journey model; credentials stay in the process environment."""
        self.ui = json.loads(Path(model_path).read_text(encoding="utf-8"))["ui"]

    def run_modelled_journey(self, payload, outcome):
        """Reset browser state, exercise one case and assert a user-visible oracle.

        No arbitrary JavaScript or Python is loaded from the model. The only
        JavaScript check inspects native HTML constraint validity. Each case
        logs only the case data, never account passwords.
        """
        robot = BuiltIn()
        browser = robot.get_library_instance("Browser")
        base = os.environ["BASE_URL"].rstrip("/")

        def navigate(path):
            """Keep declarative navigation within the selected application origin."""
            if not path.startswith("/") or path.startswith("//") or urlsplit(path).netloc:
                raise ValueError("Journey paths must be relative to the application origin.")
            robot.run_keyword("Browser.New Page", base + path)

        robot.run_keyword("Browser.New Browser", "chromium", "headless=True")
        try:
            robot.run_keyword("Browser.New Context")
            for action in self.ui.get("setup", []):
                kind = action["action"]
                if kind == "navigate":
                    navigate(action["path"])
                elif kind == "fill_env":
                    key = action["env"]
                    if key not in ("ROBOT_CUSTOMER_EMAIL", "ROBOT_CUSTOMER_PASSWORD", "ROBOT_ADMIN_EMAIL", "ROBOT_ADMIN_PASSWORD"):
                        raise ValueError("Choose an allowed Robot account environment reference.")
                    # Browser resolves the environment reference without logging the secret value.
                    browser.fill_secret(action["selector"], "%" + key)
                elif kind == "click":
                    robot.run_keyword("Browser.Click", action["selector"])
                elif kind == "wait":
                    robot.run_keyword("Browser.Wait For Elements State", action["selector"], action.get("state", "visible"))
                else:
                    raise ValueError("Unsupported journey setup action: " + kind)
            navigate(self.ui["path"])
            for name, value in json.loads(base64.b64decode(payload, validate=True).decode("utf-8")).items():
                binding = self.ui["bindings"][name]
                if binding.get("kind", "fill") == "fill":
                    browser.fill_text(binding["selector"], value)
                elif binding["kind"] == "select":
                    robot.run_keyword("Browser.Select Options By", binding["selector"], "value", value)
                else:
                    raise ValueError("Use fill or select input bindings.")
            robot.run_keyword("Browser.Click", self.ui["submit"])
            oracle = self.ui["oracles"][outcome]
            if oracle["kind"] == "native_invalid":
                invalid = robot.run_keyword("Browser.Evaluate JavaScript", oracle["selector"], "(el) => !el.checkValidity()")
                if not invalid:
                    raise AssertionError("Expected native input validation to reject this case.")
            elif oracle["kind"] == "visible_text":
                robot.run_keyword("Browser.Wait For Elements State", oracle["selector"], "visible")
                if oracle["text"] not in robot.run_keyword("Browser.Get Text", oracle["selector"]):
                    raise AssertionError("The expected visible outcome was not displayed.")
            else:
                raise ValueError("Choose a native_invalid or visible_text oracle.")
        finally:
            robot.run_keyword("Browser.Close Browser")
