"""
Safe coercion of user-supplied query/body parameters.

Several views did `int(request.query_params.get('limit', 100))` directly, which
has two problems: a non-numeric value raises ValueError and returns a 500 (any
authenticated user could generate unlimited 500s and bury real incidents in
Sentry), and an absurd value like ?limit=99999999 was accepted, serializing an
entire table into memory.

`bounded_int` coerces, clamps, and falls back instead of raising.
"""


def bounded_int(raw, default, minimum=0, maximum=None):
    """
    Coerce *raw* to an int within [minimum, maximum].

    Anything unparseable (None, '', 'abc', 12.5, a list) yields *default*
    rather than raising. The result is always clamped, so a caller can rely on
    the bounds regardless of what arrived over the wire.

    >>> bounded_int('50', default=100, maximum=500)
    50
    >>> bounded_int('abc', default=100, maximum=500)
    100
    >>> bounded_int('99999999', default=100, maximum=500)
    500
    >>> bounded_int('-5', default=100, maximum=500)
    0
    """
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default

    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


# Ceilings for the paginated list endpoints. Deliberately generous — these are
# a backstop against runaway/abusive requests, not the normal page size.
MAX_PAGE_SIZE = 500
MAX_OFFSET = 1_000_000
# Audit/usage statistics windows, in days.
MAX_STATS_DAYS = 365
