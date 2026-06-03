from __future__ import annotations

from PIL import Image

from src.process.validator import validate_image


def _make_image(tmp_path, name, w, h, color=(120, 120, 120)):
    path = tmp_path / name
    Image.new("RGB", (w, h), color).save(path)
    return path


def test_accepts_normal_image(tmp_path):
    path = _make_image(tmp_path, "ok.jpg", 800, 600)
    result = validate_image(path, min_w=300, min_h=300, min_kb=0, max_aspect=6.0)
    assert result["ok"] is True
    assert result["width"] == 800
    assert result["height"] == 600


def test_rejects_too_small(tmp_path):
    path = _make_image(tmp_path, "small.jpg", 100, 100)
    result = validate_image(path, min_w=300, min_h=300, min_kb=0, max_aspect=6.0)
    assert result["ok"] is False
    assert result["reason"] == "too_small"


def test_rejects_bad_aspect(tmp_path):
    path = _make_image(tmp_path, "wide.jpg", 4000, 400)
    result = validate_image(path, min_w=300, min_h=300, min_kb=0, max_aspect=6.0)
    assert result["ok"] is False
    assert result["reason"] == "bad_aspect"


def test_rejects_corrupt(tmp_path):
    path = tmp_path / "corrupt.jpg"
    path.write_bytes(b"not an image")
    result = validate_image(path, min_w=300, min_h=300, min_kb=0, max_aspect=6.0)
    assert result["ok"] is False
    assert result["reason"] == "decode_fail"
