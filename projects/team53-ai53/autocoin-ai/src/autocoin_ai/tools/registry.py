"""Tool registry — @tool decorator, REGISTRY, dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    fn: Callable[..., dict]


REGISTRY: Dict[str, Tool] = {}


def tool(schema: dict, description: str = ""):
    """Register a function as a named tool."""

    def decorator(fn: Callable[..., dict]) -> Callable[..., dict]:
        name = fn.__name__
        REGISTRY[name] = Tool(
            name=name,
            description=description or (fn.__doc__ or ""),
            schema=schema,
            fn=fn,
        )
        return fn

    return decorator


def dispatch(name: str, args: Dict[str, Any], run_id: Optional[str] = None) -> dict:
    if name not in REGISTRY:
        raise KeyError("unknown tool: %s" % name)
    return REGISTRY[name].fn(**args)
