import pytest
from app.services.scriptwriter.writer import ScriptWriter


def test_script_response_parsing():
    writer = ScriptWriter("openai")
    mock_json = """{
        "title": "Fed Rate Cut Analysis",
        "scenes": [
            {"order": 1, "scene_type": "hook", "title": "Hook", "text": "Breaking news on interest rates.", "visual_prompt": "Fed building"}
        ]
    }"""
    parsed = writer._parse_script_response(mock_json)
    assert parsed["title"] == "Fed Rate Cut Analysis"
    assert len(parsed["scenes"]) == 1
