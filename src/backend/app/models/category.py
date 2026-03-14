"""Compatibility shim: re-export Category from app.models.problem.

The test conftest.py imports `from app.models.category import Category`
but all models are now defined in app.models.problem.
"""
from app.models.problem import Category  # noqa: F401

__all__ = ["Category"]
