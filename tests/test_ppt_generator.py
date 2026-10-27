import os
import pytest
from ppt_generator import _compile_ppt_via_python_pptx

def test_compile_ppt_with_split_dict(tmp_path):
    out_file = str(tmp_path / "test_split.pptx")
    slides = [
        {
            "title": "AI System Architecture",
            "subtitle": "Modular Design",
            "content": {
                "left_col": {
                    "header": "Core Modules",
                    "body": "• Perception Engine\n• Decision Engine\n• Action Engine"
                },
                "right_col": {
                    "header": "Telemetry & Observability",
                    "body": "• Log streaming\n• Anomaly detection\n• Safe recovery"
                }
            }
        }
    ]
    theme = {
        "background_gradient": {"start": "#07090D", "end": "#0A1F30"},
        "text": {"primary": "#00D2FF", "secondary": "#8DA4B4"},
        "fonts": {"title": "Outfit", "body": "Outfit"},
        "accent": "#00FFCC"
    }
    success = _compile_ppt_via_python_pptx("AI", slides, theme, out_file)
    assert success is True
    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 1000

def test_compile_ppt_with_cards_and_stats(tmp_path):
    out_file = str(tmp_path / "test_cards.pptx")
    slides = [
        {
            "title": "Market Impact",
            "content": {
                "cards": [
                    {"heading": "Efficiency", "body": "40% faster latency"},
                    {"heading": "Reliability", "body": "99.9% uptime SLA"}
                ]
            }
        },
        {
            "title": "Key Metrics",
            "content": {
                "stats": [
                    {"value": "100ms", "label": "Mean Response Time"},
                    {"value": "10k+", "label": "Active Agents"}
                ]
            }
        }
    ]
    success = _compile_ppt_via_python_pptx("Enterprise Metrics", slides, {}, out_file)
    assert success is True
    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 1000
