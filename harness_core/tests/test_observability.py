from harness_core.observability import Tracer


def test_span_captures_duration():
    t = Tracer()
    with t.span("outer", k="v"):
        pass
    assert len(t.spans) == 1
    sp = t.spans[0]
    assert sp.name == "outer"
    assert sp.duration_ms is not None
    assert sp.attributes == {"k": "v"}


def test_nested_spans_link_parent():
    t = Tracer()
    with t.span("outer"):
        with t.span("inner"):
            pass
    assert len(t.spans) == 2
    inner = t.spans[0]
    outer = t.spans[1]
    assert inner.name == "inner"
    assert inner.parent_id == outer.span_id


def test_tracer_counts_metrics():
    t = Tracer()
    t.incr("foo")
    t.incr("foo", 4)
    t.incr("bar")
    assert t.metrics == {"foo": 5, "bar": 1}
