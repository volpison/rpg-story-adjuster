"""JSON parser that tracks byte spans of every scalar value in raw input.

Used by the surgical writer: given a raw byte sequence and a JSON path, find
the byte range where that scalar lives, so it can be replaced in place
without touching anything else.
"""
from __future__ import annotations
import json
import re
from typing import Any


_NUMBER = re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_WS_BYTES = b" \t\n\r"


class SpanParseError(ValueError):
    pass


def parse_with_spans(raw: bytes) -> tuple[Any, dict[tuple, tuple[int, int]]]:
    """Parse `raw`; return (value, {path: (start, end)}).

    `path` is a tuple of str keys and int indices. For scalars, `raw[start:end]`
    is the exact literal (for strings, WITHOUT the surrounding quotes; for
    numbers/bool/null, the whole literal).
    """
    spans: dict[tuple, tuple[int, int]] = {}
    i = [0]

    def ws() -> None:
        while i[0] < len(raw) and raw[i[0]:i[0] + 1] in (b" ", b"\t", b"\n", b"\r"):
            i[0] += 1

    def parse_string() -> bytes:
        if raw[i[0]:i[0] + 1] != b'"':
            raise SpanParseError(f"expected '\"' at byte {i[0]}")
        i[0] += 1
        start = i[0]
        while i[0] < len(raw):
            c = raw[i[0]:i[0] + 1]
            if c == b'"':
                content = raw[start:i[0]]
                i[0] += 1
                return content
            if c == b"\\":
                i[0] += 2
                continue
            i[0] += 1
        raise SpanParseError(f"unterminated string starting at byte {start}")

    def parse_value(path: tuple) -> Any:
        ws()
        start = i[0]
        c = raw[i[0]:i[0] + 1]

        if c == b"{":
            i[0] += 1
            ws()
            result: dict = {}
            if raw[i[0]:i[0] + 1] == b"}":
                i[0] += 1
                return result
            while True:
                ws()
                key = parse_string().decode("utf-8")
                ws()
                if raw[i[0]:i[0] + 1] != b":":
                    raise SpanParseError(f"expected ':' at byte {i[0]}")
                i[0] += 1
                result[key] = parse_value(path + (key,))
                ws()
                sep = raw[i[0]:i[0] + 1]
                if sep == b",":
                    i[0] += 1
                    continue
                if sep == b"}":
                    i[0] += 1
                    return result
                raise SpanParseError(f"expected ',' or '}}' at byte {i[0]}")

        if c == b"[":
            i[0] += 1
            ws()
            result_l: list = []
            if raw[i[0]:i[0] + 1] == b"]":
                i[0] += 1
                return result_l
            n = 0
            while True:
                result_l.append(parse_value(path + (n,)))
                ws()
                sep = raw[i[0]:i[0] + 1]
                if sep == b",":
                    i[0] += 1
                    n += 1
                    continue
                if sep == b"]":
                    i[0] += 1
                    return result_l
                raise SpanParseError(f"expected ',' or ']' at byte {i[0]}")

        if c == b'"':
            parse_string()
            # `start` is the position of the opening '"'; content begins
            # at start+1 and ends just before the closing '"'.
            spans[path] = (start + 1, i[0] - 1)
            return raw[start + 1:i[0] - 1].decode("utf-8")

        if c in (b"t", b"f", b"n"):
            j = i[0]
            while j < len(raw) and raw[j:j + 1].isalpha():
                j += 1
            word = raw[i[0]:j]
            spans[path] = (start, j)
            i[0] = j
            if word == b"true":   return True
            if word == b"false":  return False
            if word == b"null":   return None
            raise SpanParseError(f"bad literal {word!r} at byte {start}")

        m = _NUMBER.match(raw, i[0])
        if not m:
            raise SpanParseError(f"unexpected byte {c!r} at byte {i[0]}")
        i[0] = m.end()
        spans[path] = (start, i[0])
        return json.loads(raw[start:i[0]])

    value = parse_value(())
    ws()
    if i[0] != len(raw):
        raise SpanParseError(f"trailing bytes at byte {i[0]}")
    return value, spans