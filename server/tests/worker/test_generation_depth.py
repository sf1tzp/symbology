"""Unit tests for generation_depth computation.

DB-free: constructs unsaved GeneratedContent instances with a stored
``generation_depth`` and checks ``compute_generation_depth``. The legacy
fallback (chain walk via ``get_source_chain_depth``) is covered separately
in the DB-backed generated_content tests since it requires the
``source_content`` relationship.
"""
from symbology.database.generated_content import (
    GeneratedContent,
    compute_generation_depth,
)


def _content(depth):
    gc = GeneratedContent()
    gc.generation_depth = depth
    return gc


def test_no_source_is_depth_one():
    # Content generated directly from documents has no source content.
    assert compute_generation_depth(None) == 1
    assert compute_generation_depth([]) == 1


def test_single_source_increments():
    # L1 (depth 1) -> child is depth 2.
    assert compute_generation_depth([_content(1)]) == 2
    # L2 (depth 2) -> child is depth 3.
    assert compute_generation_depth([_content(2)]) == 3


def test_multiple_sources_take_max():
    # A group analysis derived from L1 and L2 sources lands one past the deepest.
    assert compute_generation_depth([_content(1), _content(2), _content(1)]) == 3


def test_depth_value_prefers_stored():
    assert _content(4)._depth_value() == 4
