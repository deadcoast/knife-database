"""KNIVVES — the visual application.

One building of pages: the entry hall (the vault, page 0) and the five
working doors, each a module under ``pages/`` with its own stylesheet.
Shared chrome — the record Plate with structural permanence across
pages, the masthead, the house laws (palette, field grammar, motion) —
lives at this level.
"""
from .app import KnivvesApp

__all__ = ["KnivvesApp"]
