from __future__ import annotations

import re

_FINAL_RE = re.compile(r"^FINAL:\s*(?P<answer>.+?)\s+(?P<citations>(?:\[E\d+\]\s*)+)$")


class FinalAnswerFormatError(ValueError):
    pass


def parse_final_answer(text: str) -> str:
    """Return the short answer from the frozen v2 `FINAL:` contract.

    Successful model output is exactly `FINAL: <short answer> [E#]` with one or
    more evidence citations. The citations remain in the product text for
    grounding validation, but are not part of answer scoring.
    """
    match = _FINAL_RE.fullmatch(text.strip())
    if match is None:
        raise FinalAnswerFormatError("answer must match 'FINAL: <short answer> [E#]'")
    answer = match.group("answer").strip()
    if not answer:
        raise FinalAnswerFormatError("short answer must not be empty")
    return answer
