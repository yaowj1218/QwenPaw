# -*- coding: utf-8 -*-
"""Registry helpers for knowledge sources and parsers."""

from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")


class Registry:
    """Simple registry for plugin-like extensibility.

    Args:
        name: Registry name for debug output.
    """

    def __init__(self, name: str):
        """Initialize registry with a name.

        Args:
            name: Registry name.

        Returns:
            None: Registry is initialized.
        """

        self._name = name
        self._items: dict[str, type[T]] = {}

    def register(self, key: str) -> Callable[[type[T]], type[T]]:
        """Register a class under the given key.

        Args:
            key: Registry key.

        Returns:
            Callable[[type[T]], type[T]]: Decorator to register the class.
        """

        def _decorator(cls: type[T]) -> type[T]:
            self._items[key] = cls
            return cls

        return _decorator

    def get(self, key: str) -> type[T] | None:
        """Get a registered class by key.

        Args:
            key: Registry key.

        Returns:
            type[T] | None: Registered class or None.
        """

        return self._items.get(key)

    def list_registered(self) -> list[str]:
        """List registered keys.

        Returns:
            list[str]: Registered keys list.
        """

        return sorted(self._items.keys())


KnowledgeSourceRegistry: Registry = Registry("knowledge_source")
ParserRegistry: Registry = Registry("knowledge_parser")
