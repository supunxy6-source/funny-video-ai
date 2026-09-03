import pytest
from app.tasks.pipeline import PIPELINE_STEPS


def test_pipeline_step_sequence():
    assert len(PIPELINE_STEPS) == 10
    step_names = [s[0] for s in PIPELINE_STEPS]
    assert step_names == [
        "discovery",
        "analysis",
        "scriptwriting",
        "visuals",
        "narration",
        "editing",
        "thumbnail",
        "seo",
        "upload",
        "notification",
    ]
