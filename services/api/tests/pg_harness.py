"""Starts a throwaway PostgreSQL (with pgvector) via the `pgserver` package. Returns None if unavailable."""
import tempfile

_server = None


def pg_url(dbname: str = "astera_test") -> str | None:
    global _server
    try:
        import pgserver
    except ImportError:
        return None
    if _server is None:
        _server = pgserver.get_server(tempfile.mkdtemp(prefix="astera_pg_"), cleanup_mode="stop")
    _server.psql(f'DROP DATABASE IF EXISTS "{dbname}";')
    _server.psql(f'CREATE DATABASE "{dbname}";')
    uri = _server.get_uri(dbname)  # postgresql://postgres:@/<db>?host=<socket dir>
    return uri.replace("postgresql://", "postgresql+psycopg://", 1)
