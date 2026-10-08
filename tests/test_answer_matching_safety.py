from evaluation.evaluate import _answer_matches


def test_bounded_wrapper_rejects_ambiguous_alternatives_and_conjunctions():
    assert _answer_matches("The project codename is Orion", ["orion"])
    assert not _answer_matches("The project codename is Orion or Atlas", ["orion"])
    assert not _answer_matches("The screen is green and blue", ["green"])
    assert not _answer_matches("Orion, maybe Atlas", ["orion"])
