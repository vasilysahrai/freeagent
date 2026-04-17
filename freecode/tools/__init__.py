"""Tool registry — every tool is a name, JSON schema, and Python callable."""

from .registry import TOOLS, dispatch, schemas

__all__ = ["TOOLS", "dispatch", "schemas"]
