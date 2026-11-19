"""Exercise real POSIX terminal output with a synthetic child, never Docker or an app."""
import errno
import os
from pathlib import Path
import pty
import re
import select
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]


class LiveTerminalTests(unittest.TestCase):
    """Gate child completion so progress observations do not depend on a short sleep."""

    def start_child(self, directory, terminal):
        """Start an output-producing child that waits for an explicit completion marker."""
        work = Path(directory)
        child = work / "child.sh"
        child.write_text("printf 'first-line\\n'\nwhile [ ! -f finish ]; do sleep 0.05; done\nprintf 'last-line'\nexit 7\n")
        script = work / "run.sh"
        script.write_text('ROOT="$PWD"\n. "$1"\nterminal_init\nterminal_live "Validate application" sh child.sh\n')
        arguments = ["sh", str(script), str(ROOT / "scripts/terminal.sh")]
        environment = os.environ.copy()
        for name in ("CI", "NO_COLOR"):
            environment.pop(name, None)
        environment.update(TERM="xterm-256color", CMDC_UI="rich", COLUMNS="64")
        master = None
        if terminal:
            master, slave = pty.openpty()
            process = subprocess.Popen(arguments, cwd=work, env=environment,
                stdout=slave, stderr=slave, start_new_session=True)
            os.close(slave)
        else:
            process = subprocess.Popen(arguments, cwd=work, env=environment,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        self.addCleanup(self.stop_child, process, master)
        return process, master if terminal else process.stdout.fileno()

    def stop_child(self, process, master):
        """Kill the complete synthetic process group on failure and close the terminal."""
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
        if master is not None:
            os.close(master)
        elif process.stdout:
            process.stdout.close()

    def read_until(self, descriptor, predicate, timeout=10):
        """Collect incremental output until an observable condition or EOF."""
        output = b""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if select.select([descriptor], [], [], 0.1)[0]:
                try:
                    block = os.read(descriptor, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not block:
                    break
                output += block
                if predicate(output):
                    return output
        self.assertTrue(predicate(output), "Expected terminal state was not observed: " + repr(output[-1000:]))
        return output

    def test_live_output_right_aligned_timer_and_original_exit_code(self):
        """Observe live text, four frames and increasing elapsed time before releasing the child."""
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as directory:
            process, descriptor = self.start_child(directory, True)
            output = self.read_until(descriptor, lambda data: b"first-line" in data and
                all(frame in data for frame in (b"[|]", b"[/]", b"[-]", b"[\\]")))
            self.assertIsNone(process.poll())
            plain = re.sub(rb"\x1b\[[0-9;?]*[A-Za-z]", b"", output)
            frames = [part for part in plain.split(b"\r") if re.search(rb"\d+\.\ds$", part)]
            self.assertTrue(frames)
            self.assertTrue(all(len(frame) == 63 for frame in frames))
            durations = [float(re.search(rb"(\d+\.\d)s$", frame)[1]) for frame in frames]
            self.assertGreater(max(durations), min(durations))
            (Path(directory) / "finish").touch()
            output += self.read_until(descriptor, lambda data: b"?25h" in data)
            self.assertIn(b"last-line", output)
            self.assertEqual(process.wait(timeout=5), 7)

    def test_redirected_output_remains_live_plain_text(self):
        """A pipe receives child output before completion without ANSI progress noise."""
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as directory:
            process, descriptor = self.start_child(directory, False)
            output = self.read_until(descriptor, lambda data: b"first-line" in data)
            self.assertIsNone(process.poll())
            (Path(directory) / "finish").touch()
            output += self.read_until(descriptor, lambda data: b"last-line" in data)
            self.assertNotIn(b"\x1b[", output)
            self.assertEqual(process.wait(timeout=5), 7)

    def test_cancellation_restores_the_cursor(self):
        """Interrupt an observed running task and require cursor restoration and failure status."""
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as directory:
            process, descriptor = self.start_child(directory, True)
            self.read_until(descriptor, lambda data: b"?25l" in data)
            os.killpg(process.pid, signal.SIGTERM)
            self.read_until(descriptor, lambda data: b"?25h" in data)
            self.assertNotEqual(process.wait(timeout=5), 0)
