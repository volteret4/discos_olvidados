import staleness


def test_albums_matches_across_accent_difference(patched_staleness):
    rows = {r["album"]: r for r in patched_staleness.get_report("albums")}

    homogenic = rows["Homogenic"]
    assert homogenic["artist"] == "Björk"
    assert homogenic["days_since"] is not None
    assert 4.5 < homogenic["days_since"] < 5.5  # ~5 días, con margen

    geogaddi = rows["Geogaddi"]
    assert geogaddi["days_since"] is not None
    assert geogaddi["days_since"] > 365


def test_album_never_scrobbled_is_none(patched_staleness):
    rows = {r["album"]: r for r in patched_staleness.get_report("albums")}
    never = rows["Nunca Escuchado"]
    assert never["last_listened"] is None
    assert never["days_since"] is None


def test_albums_preserve_local_metadata(patched_staleness):
    rows = {r["album"]: r for r in patched_staleness.get_report("albums")}
    assert rows["Geogaddi"]["genre"] == "IDM"
    assert rows["Geogaddi"]["label"] == "Warp Records"
    assert rows["Geogaddi"]["year"] == "2002"


def test_artists_report(patched_staleness):
    rows = {r["artist"]: r for r in patched_staleness.get_report("artists")}
    assert rows["Björk"]["days_since"] is not None
    assert rows["Björk"]["album_count"] == 1
    assert rows["Artista Sin Escuchas"]["days_since"] is None
    assert rows["Artista Sin Escuchas"]["album_count"] == 1


def test_get_report_caches_between_calls(patched_staleness, monkeypatch):
    calls = {"n": 0}
    real_compute = patched_staleness._compute_albums

    def counting_compute():
        calls["n"] += 1
        return real_compute()

    monkeypatch.setattr(patched_staleness, "_compute_albums", counting_compute)
    patched_staleness.get_report("albums")
    patched_staleness.get_report("albums")
    assert calls["n"] == 1  # la segunda llamada usa la caché en memoria


def test_refresh_all_recomputes(patched_staleness, monkeypatch):
    calls = {"n": 0}
    real_compute = patched_staleness._compute_albums

    def counting_compute():
        calls["n"] += 1
        return real_compute()

    monkeypatch.setattr(patched_staleness, "_compute_albums", counting_compute)
    patched_staleness.get_report("albums")
    patched_staleness.refresh_all()
    assert calls["n"] == 2
    assert patched_staleness.computed_at() is not None
