"""Check execution-mode enforcement and finite/unlimited memory configuration."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("resource_environment", ROOT / "scripts/configuration.py")
environment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(environment)


class ResourcePlanTests(unittest.TestCase):
    def setUp(self):
        """Create an isolated configuration workspace and read the real template defaults."""
        self.temp = tempfile.TemporaryDirectory(prefix="resource-test-", dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy(ROOT / ".env.template", self.root)
        shutil.copytree(ROOT / "config", self.root / "config")
        self.values = environment.parse((self.root / ".env.template").read_text())

    def test_default_allocation_matches_the_requested_finite_budget(self):
        """Allocate exactly 1920 MiB across one instance of every Compose service."""
        plan = environment.build_resource_plan(self.values)
        self.assertEqual(plan["mode"], "single")
        self.assertEqual(plan["memory_budget_mib"], 1920)
        self.assertEqual(sum(plan["memory_limits_mib"].values()), 1920)
        self.assertEqual(plan["memory_limits_mib"]["robot"], 512)

    def test_pressure_defaults_bound_swap_and_do_not_restart_failed_services(self):
        """Disable swap beyond finite RAM caps and leave failures stopped for diagnosis."""
        environment.write_resource_files(self.root, self.values)
        override = json.loads((self.root / ".runtime/compose.resources.yaml").read_text())
        self.assertEqual((self.root / ".runtime/periodic-mode").read_text(), "manual\n")
        for service in override["services"].values():
            self.assertEqual(service["memswap_limit"], service["mem_limit"])
            self.assertEqual(service["restart"], "no")
            self.assertEqual(service["pids_limit"], 128)

    def test_explicit_swap_allowance_is_added_to_each_finite_cap(self):
        """Model Docker memory-swap as RAM plus the operator-selected swap allowance."""
        self.values["CONTAINER_SWAP_ALLOWANCE_MIB"] = "64"
        self.values["PERIODIC_TASKS"] = "scheduled"
        environment.write_resource_files(self.root, self.values)
        override = json.loads((self.root / ".runtime/compose.resources.yaml").read_text())
        for service in override["services"].values():
            self.assertEqual(int(service["memswap_limit"][:-1]), int(service["mem_limit"][:-1]) + 64)
        self.assertEqual((self.root / ".runtime/periodic-mode").read_text(), "scheduled\n")

    def test_single_mode_overrides_only_effective_concurrency_not_stored_preferences(self):
        """Keep custom preferences in dotenv while enforcing one effective task and web request."""
        self.values.update(WEB_WORKERS="4", TASK_CONCURRENCY="3", WEB_THREADS="8")
        plan = environment.build_resource_plan(self.values)
        self.assertEqual(plan["effective"]["WEB_WORKERS"], "1")
        self.assertEqual(plan["effective"]["WEB_THREADS"], "1")
        self.assertEqual(plan["effective"]["TASK_POOL"], "solo")
        self.assertEqual(plan["effective"]["TASK_CONCURRENCY"], "1")
        self.assertEqual(self.values["WEB_WORKERS"], "4")

    def test_custom_mode_keeps_operator_selected_parallel_capacity(self):
        """Use explicit worker and thread settings when the operator chooses custom mode."""
        self.values.update(EXECUTION_MODE="custom", WEB_WORKERS="2", WEB_THREADS="3")
        environment.validate_resource_settings(self.values)
        plan = environment.build_resource_plan(self.values)
        self.assertEqual(plan["effective"]["WEB_WORKERS"], "2")
        self.assertEqual(plan["effective"]["WEB_THREADS"], "3")
        self.assertEqual(plan["effective"]["TASK_POOL"], "prefork")

    def test_raising_budget_scales_every_limit_and_preserves_the_exact_total(self):
        """Allow budget changes without rounding drift or an unchanged browser ceiling."""
        self.values["MEMORY_BUDGET_MIB"] = "3073"
        plan = environment.build_resource_plan(self.values)
        self.assertEqual(sum(plan["memory_limits_mib"].values()), 3073)
        self.assertGreater(plan["memory_limits_mib"]["robot"], 512)

    def test_empty_budget_disables_limits_instead_of_creating_zero_byte_containers(self):
        """Honor an explicitly empty setting as Docker/OS-managed memory capacity."""
        self.values["MEMORY_BUDGET_MIB"] = ""
        environment.validate_resource_settings(self.values)
        environment.write_resource_files(self.root, self.values)
        plan = json.loads((self.root / ".runtime/resource-plan.json").read_text())
        override = json.loads((self.root / ".runtime/compose.resources.yaml").read_text())
        self.assertIsNone(plan["memory_budget_mib"])
        self.assertFalse(plan["memory_limits_mib"])
        self.assertFalse(any("mem_limit" in service for service in override["services"].values()))
        self.assertEqual((self.root / ".runtime/bootstrap-memory.args").read_text(), "")

    def test_empty_budget_is_preserved_when_configuration_is_completed(self):
        """A blank operator value must not be silently replaced by the template's 1920 default."""
        (self.root / ".env").write_text("MEMORY_BUDGET_MIB=\n")
        environment.ensure(self.root)
        values = environment.parse((self.root / ".env").read_text())
        self.assertEqual(values["MEMORY_BUDGET_MIB"], "")

    def test_generated_single_profile_keeps_async_tasks_but_removes_prefork_children(self):
        """Use a real sequential Celery queue worker rather than replacing jobs with mocked results."""
        environment.write_resource_files(self.root, self.values)
        override = json.loads((self.root / ".runtime/compose.resources.yaml").read_text())
        worker = override["services"]["worker"]
        self.assertIn("solo", worker["command"])
        self.assertIn("--prefetch-multiplier", worker["command"])
        self.assertEqual(worker["mem_limit"], "320m")
        self.assertEqual(override["services"]["pretix"]["environment"]["NUM_WORKERS"], "1")
        self.assertIn("--threads 1", override["services"]["pretix"]["environment"]["GUNICORN_CMD_ARGS"])

    def test_generated_nginx_configuration_is_small_and_does_not_edit_source_templates(self):
        """Generate single-user Nginx settings without mutating the licensed source file."""
        source = (self.root / "config/nginx.conf").read_text()
        environment.write_resource_files(self.root, self.values)
        text = (self.root / ".runtime/nginx.conf").read_text()
        self.assertIn("worker_processes 1;", text)
        self.assertIn("worker_connections 128;", text)
        self.assertEqual(source, (self.root / "config/nginx.conf").read_text())

    def test_custom_solo_pool_rejects_misleading_parallel_concurrency(self):
        """Explain that a solo worker cannot provide two simultaneous execution slots."""
        self.values.update(EXECUTION_MODE="custom", TASK_POOL="solo", TASK_CONCURRENCY="2")
        with self.assertRaisesRegex(ValueError, "solo task pool is sequential"):
            environment.validate_resource_settings(self.values)

    def test_zero_budget_is_rejected_with_an_empty_value_recovery_hint(self):
        """Do not confuse a zero-byte limit with automatic memory management."""
        self.values["MEMORY_BUDGET_MIB"] = "0"
        with self.assertRaisesRegex(ValueError, "empty for automatic"):
            environment.validate_resource_settings(self.values)
