import http.client
import socket
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hop.src.models import Route
from hop.src.proxy import ReverseProxy
from hop.src.registry import RouteRegistry
from hop.src.scanner import PortScanner, probe


class _Hello(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><head><title>Hello title</title></head>hello</html>"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class NetworkTestCase(unittest.TestCase):
    def setUp(self):
        self.upstream = ThreadingHTTPServer(("127.0.0.1", 0), _Hello)
        self.up_port = self.upstream.server_address[1]
        threading.Thread(target=self.upstream.serve_forever, daemon=True).start()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.upstream.shutdown()
        self.upstream.server_close()
        self.tmp.cleanup()


class ProxyTests(NetworkTestCase):
    def setUp(self):
        super().setUp()
        self.registry = RouteRegistry(Path(self.tmp.name) / "r.json")
        self.registry.upsert(Route("app.hop", port=self.up_port))
        self.registry.upsert(Route("dead.hop", port=free_port()))
        self.proxy = ReverseProxy(self.registry, "http://127.0.0.1:1")
        self.port = self.proxy.start((0,))

    def tearDown(self):
        self.proxy.stop()
        super().tearDown()

    def get(self, host):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/", headers={"Host": host})
        resp = conn.getresponse()
        return resp.status, resp.read()

    def test_routes_by_host(self):
        status, body = self.get("app.hop")
        self.assertEqual(status, 200)
        self.assertIn(b"hello", body)

    def test_host_with_port_is_matched(self):
        self.assertEqual(self.get("app.hop:8080")[0], 200)

    def test_unknown_host_is_404_and_escaped(self):
        status, body = self.get("<script>.hop")
        self.assertEqual(status, 404)
        self.assertNotIn(b"<script>", body)

    def test_dead_upstream_is_502(self):
        self.assertEqual(self.get("dead.hop")[0], 502)

    def test_url_for_includes_non_default_port(self):
        self.assertEqual(self.proxy.url_for("a.hop"), f"http://a.hop:{self.port}")


class ScannerTests(NetworkTestCase):
    def test_probe_identifies_http(self):
        result = probe("127.0.0.1", self.up_port)
        self.assertEqual((result.kind, result.title), ("http", "Hello title"))

    def test_probe_closed_port(self):
        self.assertIsNone(probe("127.0.0.1", free_port(), timeout=0.3))

    def test_scan_job_finds_open_port_and_marks_self(self):
        scanner = PortScanner(own_ports=lambda: {self.up_port})
        scanner.start(self.up_port, self.up_port)
        for _ in range(100):
            snap = scanner.snapshot()
            if not snap["running"]:
                break
            time.sleep(0.05)
        self.assertEqual([(r["port"], r["is_self"]) for r in snap["results"]], [(self.up_port, True)])


if __name__ == "__main__":
    unittest.main()
