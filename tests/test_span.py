from rpg_story_adjuster.span import parse_with_spans


def test_span_simple_object():
    raw = b'{"a":1,"b":2}'
    parsed, spans = parse_with_spans(raw)
    assert parsed == {"a": 1, "b": 2}
    assert raw[spans[("a",)][0]:spans[("a",)][1]] == b"1"
    assert raw[spans[("b",)][0]:spans[("b",)][1]] == b"2"


def test_span_nested_array():
    raw = b'{"e":[null,{"list":[{"code":121,"parameters":[10,10,0]}]}]}'
    parsed, spans = parse_with_spans(raw)
    p = ("e", 1, "list", 0, "parameters", 0)
    s, e = spans[p]
    assert raw[s:e] == b"10"
    assert parsed["e"][1]["list"][0]["parameters"][0] == 10


def test_span_handles_irregular_whitespace():
    raw = b'{\n"a":1,\n"b":[10,20],\n"c":3,\n"d":{"x":4}\n}'
    parsed, spans = parse_with_spans(raw)
    assert parsed == {"a": 1, "b": [10, 20], "c": 3, "d": {"x": 4}}
    for path, expected in [
        (("a",), b"1"), (("b", 0), b"10"), (("b", 1), b"20"),
        (("c",), b"3"), (("d", "x"), b"4"),
    ]:
        s, e = spans[path]
        assert raw[s:e] == expected


def test_span_string_excludes_quotes():
    raw = b'{"name":"Hello"}'
    _, spans = parse_with_spans(raw)
    s, e = spans[("name",)]
    assert raw[s:e] == b"Hello"