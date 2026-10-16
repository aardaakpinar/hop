import json
import unittest

from hop.src.constants import (
    ErrorMessage,
    HttpHeader,
    HttpStatus,
    HttpVerb,
    MessageTemplate,
    ModelKey,
    ScanKind,
)


class ConstantsTests(unittest.TestCase):
    def test_str_enum_equality_and_json(self):
        self.assertEqual(HttpVerb.GET, "GET")
        self.assertEqual(ModelKey.HOST, "host")
        self.assertEqual(ScanKind.HTTP, "http")

        # Serializes cleanly to JSON without custom serializer
        payload = {
            ModelKey.HOST: "127.0.0.1",
            ModelKey.PORT: 8080,
            ModelKey.OK: True,
        }
        encoded = json.dumps(payload)
        self.assertIn('"host": "127.0.0.1"', encoded)
        self.assertIn('"port": 8080', encoded)
        self.assertIn('"ok": true', encoded)

    def test_status_codes(self):
        self.assertEqual(HttpStatus.OK, 200)
        self.assertEqual(HttpStatus.BAD_REQUEST, 400)
        self.assertEqual(HttpStatus.NOT_FOUND, 404)
        self.assertEqual(HttpStatus.CONFLICT, 409)

    def test_message_templates(self):
        self.assertEqual(
            MessageTemplate.reserved_by_system("hop.hop"),
            "hop.hop is reserved by the system",
        )
        self.assertEqual(
            MessageTemplate.cannot_be_deleted("hop.hop"),
            "hop.hop cannot be deleted",
        )
        self.assertEqual(
            MessageTemplate.no_route_configured("demo.hop"),
            "No route is configured for demo.hop.",
        )
        self.assertEqual(
            MessageTemplate.no_route_configured(""),
            "No route is configured for (empty host).",
        )
        self.assertEqual(
            MessageTemplate.target_not_responding("demo.hop", "127.0.0.1:3000"),
            "demo.hop (127.0.0.1:3000) is not responding.",
        )


if __name__ == "__main__":
    unittest.main()
