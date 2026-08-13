class NotFoundError(ValueError):
    """Raised when a player/team/game doesn't exist in the data at all —
    distinct from a valid name that just has zero games under the given
    filters. The API layer maps this to a 404; other ValueErrors (bad
    metric, bad direction, ...) map to a 400."""
