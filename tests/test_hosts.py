import tempfile
import unittest
from pathlib import Path

from hop.src.hosts import HostsFile


class HostsFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "hosts"
        self.path.write_text("127.0.0.1 localhost\n::1 localhost\n", encoding="utf-8")
        self.hosts = HostsFile(self.path, "hop")

    def tearDown(self):
        self.tmp.cleanup()

    def test_adds_block_and_preserves_content(self):
        result = self.hosts.sync(["cti.hop", "x.localhost"])
        text = self.path.read_text(encoding="utf-8")
        self.assertTrue(result.ok)
        self.assertIn("127.0.0.1 localhost", text)
        self.assertIn("127.0.0.1 cti.hop", text)
        self.assertNotIn("x.localhost", text)          # .localhost names need no hosts entry

    def test_idempotent(self):
        self.hosts.sync(["a.hop"])
        before = self.path.read_text(encoding="utf-8")
        self.assertEqual(self.hosts.sync(["a.hop"]).message, "hosts file is already up to date")
        self.assertEqual(before, self.path.read_text(encoding="utf-8"))

    def test_removal_restores_original(self):
        original = self.path.read_text(encoding="utf-8")
        self.hosts.sync(["a.hop"])
        self.hosts.sync([])
        self.assertEqual(self.path.read_text(encoding="utf-8").strip(), original.strip())

    def test_existing_block_is_replaced(self):
        self.hosts.sync(["a.hop", "b.hop"])
        self.hosts.sync(["c.hop"])
        text = self.path.read_text(encoding="utf-8")
        self.assertEqual(text.count("# >>> hop >>>"), 1)
        self.assertIn("127.0.0.1 c.hop", text)
        self.assertNotIn("a.hop", text)

    def test_unwritable_reports_lines(self):
        hosts = HostsFile(Path(self.tmp.name) / "missing" / "hosts", "hop")
        result = hosts.sync(["a.hop"])
        self.assertFalse(result.ok)
        self.assertEqual(result.lines, ("127.0.0.1 a.hop",))
