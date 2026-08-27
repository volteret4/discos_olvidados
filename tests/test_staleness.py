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


def test_albums_in_qbittorrent_matches_across_accents(patched_staleness):
    # trasvase/music.db tiene "Bjork" (sin acentos, collection=2) para
    # Homogenic -- debe emparejar con "Björk" igual que en lastfm_stats.db.
    rows = {r["album"]: r for r in patched_staleness.get_report("albums")}
    assert rows["Homogenic"]["in_qbittorrent"] is True


def test_albums_in_qbittorrent_false_when_absent_or_wrong_collection(patched_staleness):
    rows = {r["album"]: r for r in patched_staleness.get_report("albums")}
    # Geogaddi está en trasvase pero con collection=1 (biblioteca
    # principal, no backup) -- no cuenta como "en qBittorrent".
    assert rows["Geogaddi"]["in_qbittorrent"] is False
    # Nunca Escuchado no aparece en absoluto en trasvase.
    assert rows["Nunca Escuchado"]["in_qbittorrent"] is False


def test_artists_report(patched_staleness):
    rows = {r["artist"]: r for r in patched_staleness.get_report("artists")}
    assert rows["Björk"]["days_since"] is not None
    assert rows["Björk"]["album_count"] == 1
    assert rows["Björk"]["backed_up_count"] == 1
    assert rows["Artista Sin Escuchas"]["days_since"] is None
    assert rows["Artista Sin Escuchas"]["album_count"] == 1
    assert rows["Artista Sin Escuchas"]["backed_up_count"] == 0
    assert rows["Boards of Canada"]["backed_up_count"] == 0  # Geogaddi está en collection=1, no cuenta


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
