"""Compatibility shim: re-export User from app.models.problem.

The test conftest.py imports `from app.models.user import User`
but all models are now defined in app.models.problem.
"""
from app.models.problem import User  # noqa: F401

__all__ = ["User"]
