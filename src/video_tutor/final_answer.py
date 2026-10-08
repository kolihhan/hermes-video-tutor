from __future__ import annotations

import re

_CITATION_GROUP = r"\[(?:E\d+)(?:\s*,\s*E\d+)*\]"
_CITATION_GROUP_RE = re.compile(_CITATION_GROUP, re.IGNORECASE)
_CITATION_ID_RE = re.compile(r"E\d+", re.IGNORECASE)
_FINAL_RE = re.compile(
    rf"^FINAL:\s*(?P<answer>.+?)\s+(?P<citations>(?:{_CITATION_GROUP}\s*)+)[.!?]?$",
    re.IGNORECASE,
)


class FinalAnswerFormatError(ValueError):
    pass


def extract_citation_ids(text: str) -> tuple[str, ...]:
    ids: list[str] = []
    for group in _CITATION_GROUP_RE.findall(text):
        ids.extend(item.upper() for item in _CITATION_ID_RE.findall(group))
    return tuple(dict.fromkeys(ids))


def parse_final_answer(text: str) -> str:
    """Return the short answer from the frozen `FINAL:` contract.

    Citation groups may be written separately (``[E1] [E2]``) or together
    (``[E1, E2]``), and harmless sentence punctuation may follow the citations.
    """
    match = _FINAL_RE.fullmatch(text.strip())
    if match is None:
        raise FinalAnswerFormatError("answer must match 'FINAL: <short answer> [E#]'")
    answer = match.group("answer").strip()
    if answer.startswith("<") and answer.endswith(">"):
        answer = answer[1:-1].strip()
    if not answer:
        raise FinalAnswerFormatError("short answer must not be empty")
    return answer
