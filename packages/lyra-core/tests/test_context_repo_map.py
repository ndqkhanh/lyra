"""Tests for repo_map.py (Phase 5)."""
from __future__ import annotations

from pathlib import Path

from lyra_core.context.repo_map import (
    FunctionWindowRetriever,
    RepoMapCache,
    RepoMapEntry,
    RepoMapRanker,
    Symbol,
    SymbolExtractor,
    render_repo_map,
)


# ---------------------------------------------------------------------------
# SymbolExtractor — Python via ast
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


def test_extract_python_function(tmp_path):
    src = "def hello():\n    pass\n"
    p = _write(tmp_path, "a.py", src)
    extractor = SymbolExtractor()
    symbols = extractor.extract_file(p)
    names = [s.name for s in symbols]
    assert "hello" in names


def test_extract_python_class_and_method(tmp_path):
    src = "class Foo:\n    def bar(self):\n        pass\n"
    p = _write(tmp_path, "b.py", src)
    extractor = SymbolExtractor()
    symbols = extractor.extract_file(p)
    kinds = {s.kind for s in symbols}
    assert "class" in kinds
    assert "method" in kinds


def test_extract_python_method_has_parent(tmp_path):
    src = "class Auth:\n    def login(self):\n        pass\n"
    p = _write(tmp_path, "auth.py", src)
    symbols = SymbolExtractor().extract_file(p)
    methods = [s for s in symbols if s.kind == "method"]
    assert any(s.parent == "Auth" for s in methods)


def test_extract_python_line_numbers(tmp_path):
    src = "class A:\n    pass\n\ndef foo():\n    pass\n"
    p = _write(tmp_path, "c.py", src)
    symbols = SymbolExtractor().extract_file(p)
    foo = next(s for s in symbols if s.name == "foo")
    assert foo.line == 4


def test_extract_python_syntax_error_returns_empty(tmp_path):
    p = _write(tmp_path, "bad.py", "def (\n")
    symbols = SymbolExtractor().extract_file(p)
    assert symbols == []


def test_extract_nonexistent_file():
    symbols = SymbolExtractor().extract_file(Path("/no/such/file.py"))
    assert symbols == []


def test_extract_unsupported_extension(tmp_path):
    p = _write(tmp_path, "file.xyz", "content")
    symbols = SymbolExtractor().extract_file(p)
    assert symbols == []


def test_extract_directory(tmp_path):
    (tmp_path / "mod").mkdir()
    _write(tmp_path / "mod", "a.py", "def foo(): pass\n")
    _write(tmp_path / "mod", "b.py", "class Bar: pass\n")
    entries = SymbolExtractor().extract_directory(tmp_path)
    assert len(entries) == 2
    all_names = {s.name for e in entries for s in e.symbols}
    assert "foo" in all_names
    assert "Bar" in all_names


def test_extract_directory_skips_venv(tmp_path):
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    _write(venv, "site.py", "def hidden(): pass\n")
    _write(tmp_path, "real.py", "def visible(): pass\n")
    entries = SymbolExtractor().extract_directory(tmp_path)
    names = {s.name for e in entries for s in e.symbols}
    assert "visible" in names
    assert "hidden" not in names


# ---------------------------------------------------------------------------
# SymbolExtractor — regex-based (JS/TS/Go)
# ---------------------------------------------------------------------------


def test_extract_js_function(tmp_path):
    src = "function greet() {\n  return 'hi';\n}\n"
    p = _write(tmp_path, "a.js", src)
    symbols = SymbolExtractor().extract_file(p)
    assert any(s.name == "greet" and s.kind == "function" for s in symbols)


def test_extract_ts_class(tmp_path):
    src = "export class AuthService {\n  login() {}\n}\n"
    p = _write(tmp_path, "auth.ts", src)
    symbols = SymbolExtractor().extract_file(p)
    assert any(s.name == "AuthService" and s.kind == "class" for s in symbols)


def test_extract_go_func(tmp_path):
    src = "func Hello() string {\n  return \"hi\"\n}\n"
    p = _write(tmp_path, "main.go", src)
    symbols = SymbolExtractor().extract_file(p)
    assert any(s.name == "Hello" for s in symbols)


# ---------------------------------------------------------------------------
# RepoMapRanker
# ---------------------------------------------------------------------------


def _make_entry(file: str, *symbol_names: str) -> RepoMapEntry:
    symbols = [Symbol(name=n, kind="function", file=file, line=1) for n in symbol_names]
    return RepoMapEntry(file=file, symbols=symbols)


def test_ranker_boosts_active_files():
    ranker = RepoMapRanker()
    entries = [
        _make_entry("src/auth.py", "login"),
        _make_entry("src/utils.py", "helper"),
    ]
    ranked = ranker.rank(entries, active_files=["src/auth.py"])
    assert ranked[0].file == "src/auth.py"


def test_ranker_boosts_by_conversation():
    ranker = RepoMapRanker()
    entries = [
        _make_entry("src/auth.py", "login"),
        _make_entry("src/db.py", "query"),
    ]
    ranked = ranker.rank(entries, conversation_text="I need to fix the query function")
    assert ranked[0].file == "src/db.py"


def test_ranker_returns_all_entries():
    ranker = RepoMapRanker()
    entries = [_make_entry(f"file{i}.py", f"func{i}") for i in range(5)]
    ranked = ranker.rank(entries)
    assert len(ranked) == 5


def test_ranker_score_stored_in_entry():
    ranker = RepoMapRanker()
    entries = [_make_entry("src/auth.py", "login")]
    ranked = ranker.rank(entries, active_files=["src/auth.py"])
    assert ranked[0].score > 0.0


# ---------------------------------------------------------------------------
# FunctionWindowRetriever
# ---------------------------------------------------------------------------


def test_retrieve_python_function(tmp_path):
    src = "def foo():\n    return 42\n\ndef bar():\n    pass\n"
    p = _write(tmp_path, "mod.py", src)
    retriever = FunctionWindowRetriever()
    snippet = retriever.get(p, function_name="foo")
    assert snippet is not None
    assert "return 42" in snippet
    assert "def bar" not in snippet


def test_retrieve_python_method(tmp_path):
    src = "class A:\n    def run(self):\n        return 1\n"
    p = _write(tmp_path, "a.py", src)
    snippet = FunctionWindowRetriever().get(p, function_name="run")
    assert snippet is not None
    assert "return 1" in snippet


def test_retrieve_nonexistent_function(tmp_path):
    src = "def foo(): pass\n"
    p = _write(tmp_path, "a.py", src)
    snippet = FunctionWindowRetriever().get(p, function_name="no_such")
    assert snippet is None


def test_retrieve_missing_file():
    snippet = FunctionWindowRetriever().get(Path("/no/file.py"), function_name="foo")
    assert snippet is None


def test_retrieve_respects_max_lines(tmp_path):
    body = "\n".join(f"    x = {i}" for i in range(100))
    src = f"def big():\n{body}\n"
    p = _write(tmp_path, "big.py", src)
    snippet = FunctionWindowRetriever(max_lines=10).get(p, function_name="big")
    assert snippet is not None
    assert len(snippet.splitlines()) <= 10


# ---------------------------------------------------------------------------
# RepoMapCache
# ---------------------------------------------------------------------------


def test_cache_miss_extracts(tmp_path):
    src = "def cached(): pass\n"
    p = _write(tmp_path, "c.py", src)
    cache = RepoMapCache()
    extractor = SymbolExtractor()
    symbols = cache.get_or_extract(p, extractor)
    assert any(s.name == "cached" for s in symbols)


def test_cache_hit_returns_same(tmp_path):
    src = "def cached(): pass\n"
    p = _write(tmp_path, "c.py", src)
    cache = RepoMapCache()
    extractor = SymbolExtractor()
    s1 = cache.get_or_extract(p, extractor)
    s2 = cache.get_or_extract(p, extractor)
    assert [s.name for s in s1] == [s.name for s in s2]


def test_cache_persist_and_reload(tmp_path):
    src = "def persisted(): pass\n"
    p = _write(tmp_path, "p.py", src)
    cache_path = tmp_path / "cache.json"
    c1 = RepoMapCache(cache_path)
    c1.get_or_extract(p, SymbolExtractor())
    c2 = RepoMapCache(cache_path)
    symbols = c2.get_or_extract(p, SymbolExtractor())
    assert any(s.name == "persisted" for s in symbols)


def test_cache_invalidate(tmp_path):
    src = "def f(): pass\n"
    p = _write(tmp_path, "f.py", src)
    cache = RepoMapCache()
    extractor = SymbolExtractor()
    cache.get_or_extract(p, extractor)
    cache.invalidate(p)
    # After invalidation, re-extraction works fine
    symbols = cache.get_or_extract(p, extractor)
    assert any(s.name == "f" for s in symbols)


def test_cache_load_corrupt(tmp_path):
    cache_path = tmp_path / "bad_cache.json"
    cache_path.write_text("{bad json")
    cache = RepoMapCache(cache_path)
    assert cache._cache == {}


# ---------------------------------------------------------------------------
# render_repo_map
# ---------------------------------------------------------------------------


def test_render_includes_file_name():
    entries = [_make_entry("src/auth.py", "login", "logout")]
    output = render_repo_map(entries, token_budget=1024)
    assert "src/auth.py" in output
    assert "login" in output


def test_render_respects_token_budget():
    # Very tight budget — should truncate
    entries = [_make_entry(f"file{i}.py", *[f"func{j}" for j in range(20)]) for i in range(10)]
    output = render_repo_map(entries, token_budget=50)
    assert len(output) <= 50 * 4 + 200  # allow some slack for structure


def test_render_empty_entries():
    output = render_repo_map([], token_budget=1024)
    assert "Repository Map" in output


def test_render_shows_line_numbers():
    sym = Symbol(name="login", kind="function", file="auth.py", line=42)
    entry = RepoMapEntry(file="auth.py", symbols=[sym])
    output = render_repo_map([entry], token_budget=1024)
    assert "L42" in output
