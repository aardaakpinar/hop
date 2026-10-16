import unittest
from pathlib import Path
from unittest.mock import MagicMock

from hop.src.app import Application
from hop.src.config import Settings
from hop.src.container import Container, ContainerError, create_container
from hop.src.hosts import SyncResult
from hop.src.models import Route
from hop.src.protocols import (
    HostsManagerProtocol,
    PortScannerProtocol,
    ReverseProxyProtocol,
    RouteRegistryProtocol,
    RouteServiceProtocol,
    WebServerProtocol,
)
from hop.src.registry import RouteRegistry


class ContainerTests(unittest.TestCase):
    def test_register_and_resolve_instance(self):
        container = Container()
        obj = {"key": "val"}
        container.register_instance("my_service", obj)
        self.assertIs(container.resolve("my_service"), obj)

    def test_register_and_resolve_singleton(self):
        container = Container()
        counter = {"count": 0}

        def factory(c):
            counter["count"] += 1
            return {"instance": counter["count"]}

        container.register_singleton("singleton_service", factory)
        first = container.resolve("singleton_service")
        second = container.resolve("singleton_service")

        self.assertIs(first, second)
        self.assertEqual(counter["count"], 1)

    def test_register_and_resolve_factory(self):
        container = Container()
        counter = {"count": 0}

        def factory(c):
            counter["count"] += 1
            return {"instance": counter["count"]}

        container.register_factory("transient_service", factory)
        first = container.resolve("transient_service")
        second = container.resolve("transient_service")

        self.assertIsNot(first, second)
        self.assertEqual(counter["count"], 2)

    def test_alias(self):
        container = Container()
        container.register_singleton("target", lambda c: object())
        container.alias("alias_key", "target")

        self.assertIs(container.resolve("alias_key"), container.resolve("target"))

    def test_unregistered_key_raises_container_error(self):
        container = Container()
        with self.assertRaises(ContainerError):
            container.resolve("non_existent")

    def test_contains(self):
        container = Container()
        container.register_instance("a", 1)
        container.register_singleton("b", lambda c: 2)
        container.register_factory("c", lambda c: 3)

        self.assertIn("a", container)
        self.assertIn("b", container)
        self.assertIn("c", container)
        self.assertNotIn("d", container)


class CreateContainerTests(unittest.TestCase):
    def test_default_container_graph(self):
        settings = Settings()
        container = create_container(settings)

        self.assertIs(container.resolve(Settings), settings)
        self.assertIsInstance(container.resolve(RouteRegistryProtocol), RouteRegistryProtocol)
        self.assertIsInstance(container.resolve(HostsManagerProtocol), HostsManagerProtocol)
        self.assertIsInstance(container.resolve(RouteServiceProtocol), RouteServiceProtocol)
        self.assertIsInstance(container.resolve(ReverseProxyProtocol), ReverseProxyProtocol)
        self.assertIsInstance(container.resolve(PortScannerProtocol), PortScannerProtocol)

        # Aliases resolve to same singletons
        self.assertIs(container.resolve(RouteRegistry), container.resolve(RouteRegistryProtocol))


class IoCApplicationTests(unittest.TestCase):
    def test_application_with_custom_ioc_container(self):
        settings = Settings()
        container = create_container(settings)

        # Invert control: substitute HostsManager with a mock implementation
        mock_hosts = MagicMock()
        mock_hosts.sync.return_value = SyncResult(ok=True, message="mocked sync")
        container.register_instance(HostsManagerProtocol, mock_hosts)

        # Re-register RouteService to pick up the mocked hosts manager
        from hop.src.services import RouteService
        container.register_singleton(
            RouteServiceProtocol,
            lambda c: RouteService(
                settings=c.resolve(Settings),
                registry=c.resolve(RouteRegistryProtocol),
                hosts=c.resolve(HostsManagerProtocol),
            ),
        )

        app = Application(container)
        self.assertIs(app.hosts, mock_hosts)

        sync_result = app.routes.sync_hosts()
        self.assertTrue(sync_result.ok)
        self.assertEqual(sync_result.message, "mocked sync")
        mock_hosts.sync.assert_called_once()


if __name__ == "__main__":
    unittest.main()
