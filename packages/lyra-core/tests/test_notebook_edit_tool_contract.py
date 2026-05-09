"""Contract tests for the ``NotebookEdit`` tool."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.tools.notebook_edit import make_notebook_edit_tool


def _nb(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _write_nb(path: Path, cells: list[dict]) -> None:
    path.write_text(json.dumps(_nb(cells)), encoding="utf-8")


@pytest.fixture
def nb_path(tmp_path: Path) -> Path:
    p = tmp_path / "notebook.ipynb"
    _write_nb(
        p,
        [
            {"id": "a", "cell_type": "code", "metadata": {},
             "source": ["x = 1\n"], "outputs": [], "execution_count": None},
            {"id": "b", "cell_type": "markdown", "metadata": {},
             "source": ["# hello\n"]},
        ],
    )
    return p


def test_tool_schema_is_present(tmp_path: Path) -> None:
    tool = make_notebook_edit_tool(repo_root=tmp_path)
    assert tool.__tool_schema__["name"] == "notebook_edit"


def test_replace_by_cell_id(tmp_path: Path, nb_path: Path) -> None:
    tool = make_notebook_edit_tool(repo_root=tmp_path)
    r = tool(
        notebook_path="notebook.ipynb",
        operation="replace",
        cell_id="a",
        source="x = 42\n",
    )
    assert r["ok"], r
    data = json.loads(nb_path.read_text(encoding="utf-8"))
    assert "".join(data["cells"][0]["source"]) == "x = 42\n"


def test_insert_after_anchor(tmp_path: Path, nb_path: Path) -> None:
    tool = make_notebook_edit_tool(repo_root=tmp_path)
    r = tool(
        notebook_path="notebook.ipynb",
        operation="insert",
        cell_id="a",
        position="after",
        source="y = 2\n",
        cell_type="code",
    )
    assert r["ok"], r
    data = json.loads(nb_path.read_text(encoding="utf-8"))
    assert [c.get("id") for c in data["cells"]][:3] == ["a", None, "b"]
    assert "".join(data["cells"][1]["source"]) == "y = 2\n"


def test_delete_by_index(tmp_path: Path, nb_path: Path) -> None:
    tool = make_notebook_edit_tool(repo_root=tmp_path)
    r = tool(notebook_path="notebook.ipynb", operation="delete", index=0)
    assert r["ok"], r
    data = json.loads(nb_path.read_text(encoding="utf-8"))
    assert len(data["cells"]) == 1
    assert data["cells"][0]["id"] == "b"


def test_convert_code_to_markdown(tmp_path: Path, nb_path: Path) -> None:
    tool = make_notebook_edit_tool(repo_root=tmp_path)
    r = tool(
        notebook_path="notebook.ipynb",
        operation="convert",
        cell_id="a",
        cell_type="markdown",
    )
    assert r["ok"], r
    data = json.loads(nb_path.read_text(encoding="utf-8"))
    assert data["cells"][0]["cell_type"] == "markdown"
    assert "outputs" not in data["cells"][0]


def test_outside_repo_root_is_refused(tmp_path: Path, nb_path: Path) -> None:
    sibling = tmp_path.parent / "escaped.ipynb"
    _write_nb(sibling, [])
    tool = make_notebook_edit_tool(repo_root=tmp_path)
    r = tool(
        notebook_path="../escaped.ipynb",
        operation="delete",
        index=0,
    )
    assert r["ok"] is False
    assert "outside repo_root" in r["error"]


def test_non_ipynb_refused(tmp_path: Path) -> None:
    (tmp_path / "notreally.txt").write_text("nope", encoding="utf-8")
    tool = make_notebook_edit_tool(repo_root=tmp_path)
    r = tool(notebook_path="notreally.txt", operation="delete", index=0)
    assert r["ok"] is False
    assert "not a notebook" in r["error"]


def test_missing_cell_id_yields_friendly_error(tmp_path: Path, nb_path: Path) -> None:
    tool = make_notebook_edit_tool(repo_root=tmp_path)
    r = tool(
        notebook_path="notebook.ipynb",
        operation="replace",
        cell_id="ghost",
        source="x\n",
    )
    assert r["ok"] is False
    assert "cell_id not found" in r["error"]
