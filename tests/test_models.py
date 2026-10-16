import unittest

from hop.src.errors import ValidationError
from hop.src.models import normalize_name, validate_host, validate_port, validate_range


class NormalizeNameTests(unittest.TestCase):
    def test_appends_default_tld(self):
        self.assertEqual(normalize_name("CTI", "hop"), "cti.hop")

    def test_keeps_explicit_suffix(self):
        self.assertEqual(normalize_name("cti.test", "hop"), "cti.test")

    def test_bare_localhost_gets_suffix(self):
        self.assertEqual(normalize_name("localhost", "hop"), "localhost.hop")

    def test_rejects_invalid(self):
        for bad in ("", "-a", "a b", "a_b", "a" * 300):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                normalize_name(bad, "hop")


class ValidatorTests(unittest.TestCase):
    def test_port_bounds(self):
        self.assertEqual(validate_port("3100"), 3100)
        for bad in (0, 65536, "x", None):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                validate_port(bad)

    def test_range_order(self):
        with self.assertRaises(ValidationError):
            validate_range(500, 100)

    def test_host(self):
        self.assertEqual(validate_host(""), "127.0.0.1")
        with self.assertRaises(ValidationError):
            validate_host("a b;rm")
