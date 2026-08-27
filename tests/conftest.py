import sqlite3
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db as db_module  # noqa: E402


@pytest.fixture
def musica_local_path(tmp_path):
    path = tmp_path / "musica_local.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE artists (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE albums (
            id INTEGER PRIMARY KEY, artist_id INTEGER, name TEXT,
            year TEXT, label TEXT, genre TEXT
        );
        """
    )
    conn.executemany(
        "INSERT INTO artists (id, name) VALUES (?, ?)",
        [(1, "Björk"), (2, "Boards of Canada"), (3, "Artista Sin Escuchas")],
    )
    conn.executemany(
        "INSERT INTO albums (id, artist_id, name, year, label, genre) VALUES (?,?,?,?,?,?)",
        [
            (1, 1, "Homogenic", "1997", "One Little Indian", "Electronic"),
            (2, 2, "Geogaddi", "2002", "Warp Records", "IDM"),
            (3, 3, "Nunca Escuchado", "2020", "Indie Records", "Rock"),
        ],
    )
    conn.commit()
    conn.close()
    return str(path)


@pytest.fixture
def lastfm_stats_path(tmp_path):
    path = tmp_path / "lastfm_stats.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE artists (artist_id INTEGER PRIMARY KEY, name TEXT, name_normalized TEXT);
        CREATE TABLE albums (album_id INTEGER PRIMARY KEY, artist_id INTEGER, name TEXT, name_normalized TEXT);
        CREATE TABLE scrobbles (
            scrobble_id INTEGER PRIMARY KEY, artist_id INTEGER, album_id INTEGER,
            track TEXT, ts INTEGER, ts_iso TEXT, source TEXT
        );
        """
    )
    # "Bjork" sin acentos a propósito -- prueba la normalización NFD.
    conn.executemany(
        "INSERT INTO artists (artist_id, name, name_normalized) VALUES (?,?,?)",
        [(10, "Bjork", "bjork"), (20, "Boards of Canada", "boards of canada")],
    )
    conn.executemany(
        "INSERT INTO albums (album_id, artist_id, name, name_normalized) VALUES (?,?,?,?)",
        [(100, 10, "Homogenic", "homogenic"), (200, 20, "Geogaddi", "geogaddi")],
    )
    now = int(time.time())
    recent_ts = now - 5 * 86400       # hace 5 días
    old_ts = now - 400 * 86400        # hace >1 año
    conn.executemany(
        "INSERT INTO scrobbles (artist_id, album_id, track, ts, ts_iso, source) VALUES (?,?,?,?,?,?)",
        [
            (10, 100, "Jóga", recent_ts, "x", "lastfm"),
            (10, 100, "Bachelorette", recent_ts - 100, "x", "lastfm"),
            (20, 200, "Alpha and Omega", old_ts, "x", "lastfm"),
        ],
    )
    conn.commit()
    conn.close()
    return str(path)


@pytest.fixture
def trasvase_path(tmp_path):
    path = tmp_path / "music.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE artists (id INTEGER PRIMARY KEY, name TEXT UNIQUE, mbid TEXT);
        CREATE TABLE albums (
            id INTEGER PRIMARY KEY, artist_id INTEGER, title TEXT, label TEXT,
            genre TEXT, year INTEGER, path TEXT UNIQUE, collection INTEGER, mbid TEXT
        );
        """
    )
    # "Bjork" (sin acentos, como en lastfm_stats.db) -- prueba que el
    # cruce con qBittorrent también normaliza. Solo Homogenic está
    # respaldada; Geogaddi y Nunca Escuchado no aparecen aquí.
    conn.execute("INSERT INTO artists (id, name) VALUES (1, 'Bjork')")
    conn.execute(
        "INSERT INTO albums (artist_id, title, path, collection) VALUES (1, 'Homogenic', '/mnt/music/coleccion2/bjork-homogenic', 2)"
    )
    # Fila en collection=1 (biblioteca principal de trasvase, no backup)
    # que NO debe contar como "en qBittorrent".
    conn.execute("INSERT INTO artists (id, name) VALUES (2, 'Boards of Canada')")
    conn.execute(
        "INSERT INTO albums (artist_id, title, path, collection) VALUES (2, 'Geogaddi', '/mnt/music/coleccion1/boc-geogaddi', 1)"
    )
    conn.commit()
    conn.close()
    return str(path)


@pytest.fixture
def patched_db(monkeypatch, musica_local_path, lastfm_stats_path, trasvase_path):
    monkeypatch.setattr(db_module, "MUSICA_LOCAL_DB", musica_local_path)
    monkeypatch.setattr(db_module, "LASTFM_DB", lastfm_stats_path)
    monkeypatch.setattr(db_module, "TRASVASE_DB", trasvase_path)
    return db_module


@pytest.fixture
def patched_staleness(patched_db, monkeypatch):
    import staleness
    monkeypatch.setitem(staleness._CACHE, "albums", None)
    monkeypatch.setitem(staleness._CACHE, "artists", None)
    monkeypatch.setitem(staleness._CACHE, "computed_at", None)
    return staleness
