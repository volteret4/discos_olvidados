"""Normalización de nombres para cruzar musica_local.sqlite (biblioteca
propia) con lastfm_stats.db (scrobbles) -- misma función que
services/lastfm_explorer/normalize.py, deliberadamente distinta de la de
lastfm_stats.db (solo minúsculas + espacios, sin quitar acentos)."""
import re
import unicodedata


def normalize(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.strip().lower()
    return re.sub(r"\s+", " ", s)
