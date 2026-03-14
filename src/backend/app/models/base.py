"""Compatibility shim: re-export Base from app.core.database.

The conftest.py imports `from app.models.base import Base` to create tables
for the test DB. The canonical definition lives in app.core.database; this
module simply re-exports it so the import path is satisfied.
"""
from app.core.database import Base  # noqa: F401

__all__ = ["Base"]
