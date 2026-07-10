# apps/api/tests/test_vision_tools_path.py
from __future__ import annotations

import sys

from app.services.vision_tools_path import ensure_vision_tools_on_path
from app.storage.database import ROOT


def test_it_puts_vision_tools_on_sys_path():
    ensure_vision_tools_on_path()
    assert str(ROOT / "apps" / "vision-tools") in sys.path


def test_calling_it_twice_does_not_add_a_second_entry():
    ensure_vision_tools_on_path()
    ensure_vision_tools_on_path()
    entry = str(ROOT / "apps" / "vision-tools")
    assert sys.path.count(entry) == 1


def test_compute_button_offsets_becomes_importable():
    ensure_vision_tools_on_path()
    from scripts.logo_anchor import compute_button_offsets

    offsets = compute_button_offsets(
        {"x": 0, "y": 0, "width": 10, "height": 10},
        {"a": {"x": 10, "y": 0, "width": 5, "height": 5}},
    )
    # (button_cx - logo_cx) / logo_width = ((10 + 5 / 2) - (0 + 10 / 2)) / 10
    assert offsets["a"]["dx"] == 0.75
