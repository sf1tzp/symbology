"""Unit tests for word-level text diffing (pure functions, no DB)."""
from symbology.utils.text_diff import (
    classify_change,
    compute_token_diff,
    edit_ratio,
    DE_EMPHASISED,
    ESCALATED,
    REWORDED,
    UNCHANGED,
)

# The §1A.7 FY24 → FY25 example from the design mockup (screen-changes-report.jsx).
FY24 = (
    "Certain of our Electronic Technologies Group products rely on specialized "
    "semiconductor components for which alternative suppliers may not be readily "
    "available. A loss of supply or substantial price increases in these components "
    "could materially affect our ability to manufacture, deliver, or service these "
    "products and could harm our financial results.\n\n"
    "We seek to qualify second sources where commercially practicable, but the "
    "certification cycle for replacement components can extend twelve to twenty-four "
    "months in certain defense applications."
)
FY25 = (
    "A meaningful portion of our Electronic Technologies Group products depend on "
    "semiconductor components sourced from foundries located in Taiwan, including "
    "several single-source suppliers identified in our supply chain risk assessments. "
    "A loss of supply or substantial price increases from these suppliers could "
    "materially affect our ability to manufacture, deliver, or service these products "
    "and could harm our financial results.\n\n"
    "We seek to qualify second sources where commercially practicable, but the "
    "certification cycle for replacement components can extend twelve to twenty-four "
    "months in certain defense applications. Geopolitical tensions in the Taiwan "
    "Strait, including export-control regimes affecting advanced-node semiconductor "
    "manufacturing, represent an additional layer of supply uncertainty for which "
    "alternative sourcing may not be available at any cost."
)


def _left(ops):
    return "".join(o["text"] for o in ops if o["op"] in ("equal", "delete"))


def _right(ops):
    return "".join(o["text"] for o in ops if o["op"] in ("equal", "insert"))


def test_ops_losslessly_reconstruct_both_columns():
    ops, _, _ = compute_token_diff(FY24, FY25)
    assert _left(ops) == FY24
    assert _right(ops) == FY25


def test_ops_have_valid_shape_and_share_an_equal_segment():
    ops, added, removed = compute_token_diff(FY24, FY25)
    assert all(set(o) == {"op", "text"} for o in ops)
    assert all(o["op"] in ("equal", "insert", "delete") for o in ops)
    # The unchanged "We seek to qualify second sources..." sentence survives as equal.
    assert any(o["op"] == "equal" and "qualify second sources" in o["text"] for o in ops)
    # FY25 adds substantially more than it removes.
    assert added > removed > 0


def test_identical_text_is_unchanged():
    ops, added, removed = compute_token_diff(FY24, FY24)
    assert added == 0 and removed == 0
    assert all(o["op"] == "equal" for o in ops)
    assert edit_ratio(FY24, FY24, ops) == 0.0
    assert classify_change(FY24, FY24, ops) == UNCHANGED


def test_escalated_when_materially_longer():
    ops, _, _ = compute_token_diff(FY24, FY25)
    assert classify_change(FY24, FY25, ops) == ESCALATED


def test_de_emphasised_when_materially_shorter():
    ops, _, _ = compute_token_diff(FY25, FY24)  # reverse: current is much shorter
    assert classify_change(FY25, FY24, ops) == DE_EMPHASISED


def test_reworded_when_similar_length_small_edit():
    prev = "The quick brown fox jumps over the lazy dog every single morning without fail."
    curr = "The quick red fox leaps over the lazy dog every single morning without fail."
    ops, _, _ = compute_token_diff(prev, curr)
    assert _left(ops) == prev
    assert _right(ops) == curr
    assert classify_change(prev, curr, ops) == REWORDED
