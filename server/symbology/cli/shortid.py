"""Short, copy-pasteable ids for UUID-keyed objects in the CLI.

uuid7 ids are time-ordered, so their *leading* segments collide for objects
created in the same millisecond; the trailing segment (the random tail) stays
distinct. So we surface and accept that segment — the UUID analogue of the
content-hash short ids (``get_short_hash``) used for hash-keyed objects.

Use ``short_id(obj.id)`` when rendering an id column, and ``resolve_id(Model, value)``
to turn a user-supplied full UUID or short id back into a concrete id.
"""
from uuid import UUID

import click
from sqlalchemy import String, cast, func

from symbology.database.base import get_db_session


def short_id(value) -> str:
    """The display short id for a UUID: its last segment (after the final hyphen)."""
    return str(value).rsplit("-", 1)[-1]


def maybe_short_id(value) -> str:
    """``short_id(value)`` if it's a UUID, else the value unchanged.

    For mixed columns/strings where a field may hold a UUID or something else (an
    accession number, a ticker) — only UUIDs get shortened.
    """
    try:
        UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return str(value)
    return short_id(value)


def resolve_id(model, value: str, *, kind: str = "object") -> str:
    """Resolve a full UUID or a short id (the UUID's last segment) to one ``model.id``.

    A full UUID is returned as-is (no lookup). Otherwise ``value`` is matched against
    the last segment of ``model.id``: a unique match returns that id, while no match
    or an ambiguous one raises ``click.ClickException`` (listing candidates) so the
    caller need only let it propagate. ``kind`` names the object in messages.
    """
    s = (value or "").strip()
    if not s:
        raise click.ClickException(f"No {kind} id provided")
    try:
        UUID(s)
        return s  # already a full uuid — skip the lookup
    except ValueError:
        pass
    session = get_db_session()
    last_segment = func.split_part(cast(model.id, String), "-", 5)
    ids = [
        str(r[0])
        for r in session.query(model.id).filter(last_segment.like(f"{s}%")).limit(11).all()
    ]
    if not ids:
        raise click.ClickException(f"No {kind} matches short id '{s}'")
    if len(ids) > 1:
        listed = "\n".join(f"  {i}" for i in ids[:10])
        more = "\n  …" if len(ids) > 10 else ""
        raise click.ClickException(
            f"Ambiguous short id '{s}' matches {len(ids)} {kind}s — add more characters:\n{listed}{more}"
        )
    return ids[0]
