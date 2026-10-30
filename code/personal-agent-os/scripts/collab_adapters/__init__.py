"""PAOS Collaboration Watcher 的 Runtime Adapter 包。"""
from collab_adapters.base import BaseAdapter
from collab_adapters.manual import ManualAdapter
from collab_adapters.mock import MockAdapter
from collab_adapters.command import CommandAdapter
from collab_adapters.self import SelfAdapter

SUPPORTED_ADAPTERS_MAP = {
    "manual": ManualAdapter,
    "mock": MockAdapter,
    "command": CommandAdapter,
    "self": SelfAdapter,
}

__all__ = [
    "BaseAdapter",
    "ManualAdapter",
    "MockAdapter",
    "CommandAdapter",
    "SelfAdapter",
    "SUPPORTED_ADAPTERS_MAP",
]
