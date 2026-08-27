import os
import sqlite3

LASTFM_DB = os.environ.get("LASTFM_DB", "/data/lastfm_stats.db")
MUSICA_LOCAL_DB = os.environ.get("MUSICA_LOCAL_DB", "/musica_local.sqlite")


def get_lastfm_conn() -> sqlite3.Connection:
    # immutable=1 -- lastfm_data se monta :ro en Docker; mode=ro solo no
    # basta ahí (falla en la primera query real, no al conectar). Mismo
    # problema ya documentado en services/lastfm_explorer/db.py.
    conn = sqlite3.connect(f"file:{LASTFM_DB}?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_musica_local_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{MUSICA_LOCAL_DB}?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    return conn
