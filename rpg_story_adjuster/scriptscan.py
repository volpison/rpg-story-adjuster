from __future__ import annotations
import re
from typing import Iterator

_SWITCH_GET = re.compile(r"\$gameSwitches\.value\(")
_SWITCH_SET = re.compile(r"\$gameSwitches\.setValue\(")
_VAR_GET = re.compile(r"\$gameVariables\.value\(")
_VAR_SET = re.compile(r"\$gameVariables\.setValue\(")


def scan_script(text: str, kind: str) -> Iterator[tuple[int | None, str, bool]]:
    """Yield (value_or_None, snippet, is_dynamic) for script refs of `kind`.

    `value=10` in `$gameSwitches.value(10)` is literal; `$gameSwitches.value(10+1)`
    and `$gameSwitches.value(x)` are dynamic (not rewritten; reported).
    """
    patterns = (_SWITCH_GET, _SWITCH_SET) if kind == "switch" else (_VAR_GET, _VAR_SET)
    for pat in patterns:
        for m in pat.finditer(text):
            pos = m.end()
            is_set = "setValue" in m.group(0)
            terminator = "," if is_set else ")"
            lit = re.match(r"\s*(\d+)\s*", text[pos:])
            if lit:
                after = text[pos + lit.end():]
                if after.startswith(terminator):
                    yield (int(lit.group(1)),
                           text[m.start():pos + lit.end() + 1], False)
                    continue
            end = text.find(")", pos)
            end = len(text) if end == -1 else end + 1
            yield (None, text[m.start():end], True)
