"""Anonymous visit logging for the request_log table (see db/schema.sql).
Lets you answer "how many queries" and "how many distinct visitors" without
any accounts or sessions -- a visitor is approximated by a salted hash of
their IP address, never the raw IP itself.

Like engine/live_db.py, this only does anything when DATABASE_URL is set;
unset, log_query() is a no-op, so local dev/CI/tests are unaffected. A
logging failure (DB down, bad credentials) is caught and swallowed here --
an API response should never fail because analytics couldn't be written.
"""

import hashlib
import logging
import os

from fastapi import Request

logger = logging.getLogger(__name__)


def _visitor_hash(ip: str) -> str:
    """sha256(salt + ip), truncated -- irreversible without the salt. IPv4
    space is only ~4 billion addresses, small enough to brute-force without
    a secret salt, so VISITOR_HASH_SALT must be set to something private in
    production (an unset salt still runs, it just isn't actually anonymous)."""
    salt = os.environ.get("VISITOR_HASH_SALT", "")
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:16]


def _client_ip(request: Request) -> str:
    """Render (like most PaaS platforms) sits behind a proxy, so
    request.client.host is the proxy's own IP, not the visitor's -- the
    real address is the first entry in X-Forwarded-For when present."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def log_query(request: Request, endpoint: str) -> None:
    """Fire-and-forget: records one row (endpoint, visitor_hash, timestamp)
    to Postgres. No-ops without DATABASE_URL; swallows any failure so a
    logging hiccup never turns into a 500 for the actual request."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return

    visitor_hash = _visitor_hash(_client_ip(request))
    try:
        import psycopg

        with psycopg.connect(database_url, connect_timeout=3) as conn:
            conn.execute(
                "INSERT INTO request_log (endpoint, visitor_hash) VALUES (%s, %s)",
                (endpoint, visitor_hash),
            )
    except Exception:
        logger.exception("failed to log query visit for %s", endpoint)
