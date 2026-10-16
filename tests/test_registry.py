import json
import tempfile
import unittest
from pathlib import Path

from hop.src.errors import ConflictError
from hop.src.models import Route
from hop.src.registry import RouteRegistry


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.panel = Route("hop.hop", port=7777, builtin=True)

    def tearDown(self):
        self.tmp.cleanup()

    def make(self):
        return RouteRegistry(self.dir / "routes.json", builtin=[self.panel])

    def test_persistence_roundtrip(self):
        self.make().upsert(Route("a.hop", port=3000, rewrite_host=True))
        route = self.make().get("a.hop")
        self.assertEqual((route.port, route.rewrite_host), (3000, True))

    def test_builtin_is_protected_and_not_persisted(self):
        reg = self.make()
        with self.assertRaises(ConflictError):
            reg.upsert(Route("hop.hop", port=1))
        with self.assertRaises(ConflictError):
            reg.remove("hop.hop")
        reg.upsert(Route("a.hop", port=3000))
        self.assertNotIn("hop.hop", json.loads((self.dir / "routes.json").read_text()))
        self.assertEqual(reg.all()[0].name, "hop.hop")       # the panel always comes first

    def test_remove(self):
        reg = self.make()
        reg.upsert(Route("a.hop", port=3000))
        self.assertTrue(reg.remove("a.hop"))
        self.assertFalse(reg.remove("a.hop"))

    def test_corrupt_file_is_ignored(self):
        (self.dir / "routes.json").write_text("{broken")
        self.assertEqual([r.name for r in self.make().all()], ["hop.hop"])
