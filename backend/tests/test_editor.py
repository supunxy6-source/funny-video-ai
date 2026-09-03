import pytest
from app.services.editor.assets import COLORS, FONT_SIZES


def test_editor_asset_colors():
    assert "primary" in COLORS
    assert "accent" in COLORS
    assert FONT_SIZES["title"] in (60, 64)

