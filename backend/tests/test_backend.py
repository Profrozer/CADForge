"""Backend tests — sandbox execution, failure classification, code extraction,
storage, and the full pipeline via the mock provider. No AI keys needed."""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.providers.base import ProviderError, extract_code
from app.providers.mock_provider import BRACKET_CODE, MockProvider
from app.sandbox.runner import execute_cadquery

GOOD_CODE = """
import cadquery as cq
result = cq.Workplane("XY").box(20, 10, 5).faces(">Z").workplane().hole(4)
"""

SYNTAX_ERROR_CODE = "import cadquery as cq\nresult = cq.Workplane('XY').box(20, 10,"

NO_RESULT_CODE = "x = 1 + 1"

GEOMETRY_ERROR_CODE = """
import cadquery as cq
# fillet radius far larger than the box -> OCC failure
result = cq.Workplane("XY").box(2, 2, 2).edges().fillet(50)
"""


def test_sandbox_executes_and_exports(tmp_path):
    res = execute_cadquery(GOOD_CODE, str(tmp_path), timeout=120)
    assert res["ok"], res
    for fmt in ("step", "stl", "obj"):
        assert fmt in res["exports"]
        assert (tmp_path / f"model.{fmt}").stat().st_size > 0
    assert res["stats"]["bbox_mm"] == [20.0, 10.0, 5.0]


def test_sandbox_flat_part_gets_dxf(tmp_path):
    res = execute_cadquery(GOOD_CODE, str(tmp_path), timeout=120)
    assert res["ok"]
    assert "dxf" in res["exports"], res.get("export_errors")


def test_sandbox_classifies_python_error(tmp_path):
    res = execute_cadquery(SYNTAX_ERROR_CODE, str(tmp_path), timeout=60)
    assert not res["ok"]
    assert res["kind"] == "python_error"
    assert "SyntaxError" in res["error"]


def test_sandbox_classifies_no_result(tmp_path):
    res = execute_cadquery(NO_RESULT_CODE, str(tmp_path), timeout=60)
    assert not res["ok"]
    assert res["kind"] == "no_result"


def test_sandbox_classifies_geometry_error(tmp_path):
    res = execute_cadquery(GEOMETRY_ERROR_CODE, str(tmp_path), timeout=120)
    assert not res["ok"]
    assert res["kind"] in ("python_error", "geometry_invalid")


def test_sandbox_blocks_network(tmp_path):
    code = """
import cadquery as cq
import urllib.request
urllib.request.urlopen("http://example.com")
result = cq.Workplane("XY").box(1, 1, 1)
"""
    res = execute_cadquery(code, str(tmp_path), timeout=60)
    assert not res["ok"]
    assert "Network access is disabled" in res["error"]


def test_extract_code_strips_fences():
    text = "Here you go:\n```python\nimport cadquery as cq\nresult = cq.Workplane()\n```\nEnjoy!"
    assert extract_code(text).startswith("import cadquery")


def test_extract_code_rejects_prose():
    with pytest.raises(ProviderError):
        extract_code("I'm sorry, I can't help with that.")


def test_mock_provider_bracket_runs(tmp_path):
    provider = MockProvider()
    code = asyncio.run(provider.generate("anything"))
    assert code == BRACKET_CODE
    res = execute_cadquery(code, str(tmp_path), timeout=120)
    assert res["ok"], res


def test_storage_roundtrip(tmp_path, monkeypatch):
    from app import storage

    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "PARTS_DIR", tmp_path / "parts")
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")

    pid = storage.new_part_id()
    assert storage.next_version(pid) == 1
    storage.save_version(pid, 1, prompt="a box", spec="spec", code="code",
                         provider="mock", model="m", exports={"step": "model.step"},
                         stats={})
    assert storage.next_version(pid) == 2
    hist = storage.list_history()
    assert len(hist) == 1 and hist[0]["part_id"] == pid
    assert storage.get_version(pid, 1)["exports"] == {"step": "model.step"}
    storage.delete_part(pid)
    assert storage.list_history() == []
